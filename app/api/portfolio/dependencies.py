import asyncio
import re
import ast
from datetime import datetime, timedelta
import json
from typing import Annotated
from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import dependencies as auth_dependencies
from app.core.errors import errors
from app.core.models import db_helper
from . import crud
from .schemas import PortfolioResponse, PortfolioCreate, SimilarAssetsResponse, PortfolioResponseExtended, \
    ConnectTelegram, SentimentScore
from app.core.modules_factory import cmc_driver, perplexity_driver, elfa_driver, coin_gecko_driver, redis_db, \
    llama, twitter_scraper
from utils.general import create_crypto_sentiment_chart, parse_json_string
from utils import prompts


async def create_portfolio(
        portfolio_data: PortfolioCreate,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> PortfolioResponse:
    result = await crud.create(session=session, portfolio_data=portfolio_data)
    return PortfolioResponse.from_orm(result)


async def connect_tg(
        users_data: ConnectTelegram,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    user = await auth_dependencies.check_wallet(wallet_address=users_data.wallet, session=session)
    user.telegram_id = users_data.telegram_id
    await session.commit()
    return True


async def get_all_portfolio(
        telegram_id: Annotated[str, Path],
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> list[PortfolioResponse]:
    res = await crud.get_users_assets(session=session, telegram_id=telegram_id)
    return res


async def get_selected_portfolio(
        symbol: Annotated[str, Path],
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),

) -> PortfolioResponseExtended:
    portfolio = await crud.get_by_symbol(session=session, symbol=symbol)
    cash_data = await redis_db.get(portfolio.symbol)
    if cash_data:
        return PortfolioResponseExtended.parse_obj(json.loads(cash_data.decode("UTF-8")))
    if not portfolio:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors.portfolio_errors.PROJECT_NOT_FOUND
        )
    response_data = PortfolioResponseExtended.from_orm(portfolio)
    response_data.current_price = cmc_driver.get_current_token_price(symbol=portfolio.symbol)
    full_token_name = coin_gecko_driver.get_data_over_coingecko_id(token_id=portfolio.coingecko_id).get("name")
    response_data = await create_report(
        symbol=portfolio.symbol,
        full_token_name=full_token_name,
        data=response_data,
        twitter=portfolio.twitter
    )
    # response_data = await generate_full_report(data=response_data)
    await redis_db.set(portfolio.symbol, response_data.json(), ex=86400)
    return response_data


async def get_sentiment_score(
        symbol: Annotated[str, Path],
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),

) -> SentimentScore:
    portfolio = await crud.get_by_symbol(session=session, symbol=symbol)
    if not portfolio:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors.portfolio_errors.PROJECT_NOT_FOUND
        )

    cash_data = await redis_db.get(f"{portfolio.symbol}_sentiment")
    if cash_data:
        return SentimentScore.parse_obj(json.loads(cash_data.decode("UTF-8")))
    full_token_name = coin_gecko_driver.get_data_over_coingecko_id(token_id=portfolio.coingecko_id).get("name")
    cash_data = await redis_db.get(f"{portfolio.symbol}_elfa")
    if not cash_data:
        sentiment_score = elfa_driver.get_squeeze(symbol=portfolio.symbol, full_token_name=full_token_name)
        await redis_db.set(f"{portfolio.symbol}_elfa", str(sentiment_score), ex=86400)
    else:
        sentiment_score = ast.literal_eval(cash_data.decode("UTF-8"))
    for post in sentiment_score:
        is_post_about_crypto = llama.send_message(
            prompt="You are data analyzer to define relation data to crypto asset.",
            message=f"Process data: {post.get('content')} and define is this data related to crypto asset ${portfolio.symbol} or {full_token_name} project. #Answer one word only: Yes or Not.")
        clean_response = re.sub(r'[^a-zA-Z\s]', '', is_post_about_crypto.replace("</s>", "")).lower()
        if clean_response == 'not':
            sentiment_score.remove(post)
            continue
        score = llama.send_message(
            prompt=prompts.bullish_fud_score_prompt % portfolio.symbol,
            message=f"Score twitter post about ${portfolio.symbol} ({full_token_name} project): {post.get('content')}. #Answer only number!"
        )
        post["score"] = int(extract_rating(score))
    sorted_score_list = sorted(sentiment_score, key=lambda x: x.get("score", 0), reverse=True)
    bullish_post = llama.send_message(
            prompt=prompts.top_1_bullish % portfolio.symbol,
            message=f"Choose TOP 1 Bullish twitter post about ${portfolio.symbol} ({full_token_name} project): {sorted_score_list[:5]}."
        )

    fud_post = llama.send_message(
        prompt=prompts.top_1_fud % portfolio.symbol,
        message=f"Choose TOP 1 Bearish/FUD twitter post about ${portfolio.symbol} ({full_token_name} project): {sorted_score_list[-5:]}."
    )
    bullish = await create_twitt_url(data=json.loads(bullish_post.replace("</s>", "")))
    fud = await create_twitt_url(data=json.loads(fud_post.replace("</s>", "")))
    response_data = SentimentScore(bullish=bullish, fud=fud)
    await redis_db.set(f"{portfolio.symbol}_sentiment", response_data.json(), ex=86400)
    return response_data

def extract_rating(text):
    """Extracts the rating number from the LLM response."""

    match = re.search(r'(?:\w+: )?(\d+)', text)  # Find digits before " out of"
    if match:
        return match.group(1)  # Return the captured digits
    else:
        return 0


async def create_twitt_url(data: dict):
    twitter_id, twitter_user_id = data.get("twitter_id"), data.get("twitter_user_id")
    username = await twitter_scraper.get_username_by_user_id(user_id=twitter_user_id)
    return f"https://x.com/{username}/status/{twitter_id}"


async def create_report(
        symbol: str,
        full_token_name: str,
        data: PortfolioResponseExtended,
        twitter: str = None
):
    for k, v in prompts.prompts.items():
        # perplexity_check = perplexity_driver.chat_without_streaming(
        #     message=f"Answer only one word if any news about{full_token_name}",
        #     prompt=v.get("check") % symbol
        # )
        # if perplexity_check.lower() == "no":
        #     setattr(data, k, "No updates")
        # else:
        perplexity_result = perplexity_driver.chat_without_streaming(
            message=v.get("msg") % (
                symbol, full_token_name, twitter, datetime.now() - timedelta(days=7), datetime.now()),
            prompt=v.get("perplexity_prompt") % (symbol, datetime.now() - timedelta(days=7), datetime.now())
        )
        llama_processing = llama.send_message(message=perplexity_result.replace("</s>", ""),
                                              prompt=v.get("chatgpt_prompt"))
        setattr(data, k, llama_processing)
    cash_data = await redis_db.get(f"{symbol}_twitter_posts")
    if not cash_data:
        twitts_over_asset = await twitter_scraper.fetch_tweets(protocol_name=twitter.split("/")[-1])
        await redis_db.set(f"{symbol}_twitter_posts", str(twitts_over_asset), ex=86400)
    else:
        twitts_over_asset = ast.literal_eval(cash_data.decode("UTF-8"))
    if twitts_over_asset:
        msg = f"There is data from official {twitter} over {full_token_name} ${symbol} {twitts_over_asset}"
        data.twitter_news = llama.send_message(message=msg, prompt=prompts.twikit_prompt).replace("</s>", "")
    return data


async def generate_full_report(
        data: PortfolioResponseExtended,
):
    # message = f"""Generate report according to base prompt rules. Token ticker: {data.symbol},
    #             data on which the report should be based: {data.twitter_news}.
    #             Remove duplicate news, leaving only one."""
    # data.related_news = llama.send_message(
    #     message=message,
    #     prompt=prompts.final_updates_prompt
    # ).removesuffix("</s>")
    message = f"""Generate report according to base prompt rules. Token ticker: {data.symbol}, 
                data on which the report should be based: {data.price_movements}."""
    data.price_movements = llama.send_message(
        message=message,
        prompt=prompts.final_price_movements_prompt
    ).replace("</s>", "")

    return data


async def get_selected_portfolio_chart(
        symbol: Annotated[str, Path],
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
) -> bytes:
    portfolio = await crud.get_by_symbol(session=session, symbol=symbol)
    cash_data = await redis_db.get(f"{portfolio.symbol}_graph")
    if cash_data:
        return cash_data
    if not portfolio:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors.portfolio_errors.PROJECT_NOT_FOUND
        )
    historical_price = coin_gecko_driver.get_historical_prices(coingecko_id=portfolio.coingecko_id)
    # sentiment_score = elfa_driver.get_top_posts(symbol=portfolio.symbol)
    response_data = create_crypto_sentiment_chart(historical_prices=historical_price)
    await redis_db.set(f"{portfolio.symbol}_graph", response_data.getvalue(), ex=86400)
    return response_data.getvalue()


async def get_similar_assets(
        asset_symbol: str,
        token_id: str = None,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
) -> list[SimilarAssetsResponse] | SimilarAssetsResponse:
    similar_assets = coin_gecko_driver.get_similar_tokens(symbol=asset_symbol)
    result = [SimilarAssetsResponse.from_orm(asset) for asset in similar_assets]
    coingecko_ids = await crud.get_similar_assets(session=session, symbol=asset_symbol)
    for _id in coingecko_ids:
        data = coin_gecko_driver.get_data_over_coingecko_id(token_id=_id)
        result.insert(0, SimilarAssetsResponse.from_orm(data))
    if token_id:
        token = list(filter(lambda x: token_id == x.token_id, result))
        result = SimilarAssetsResponse.from_orm(token[0])
        result.twitter = coin_gecko_driver.get_twitter_from_coingecko(token_id=result.token_id)
    return result


async def delete_portfolio(
        telegram_id: str,
        symbol: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
):
    result = await crud.delete_users_portfolio(session=session, telegram_id=telegram_id, symbol=symbol)
    return result


async def get_dataset(session: AsyncSession = Depends(db_helper.scoped_session_dependency)):
    all_tokens = await crud.get_all(session=session)
    with open("data.txt", "a", encoding="utf-8") as file:
        for token in all_tokens:
            full_token_name = coin_gecko_driver.get_data_over_coingecko_id(token_id=token.coingecko_id).get("name")
            file.write(full_token_name + "\n")
            sentiment_score = elfa_driver.get_squeeze(symbol=token.symbol)
            file.write("=" * 100)
            file.write("\n" + f"SENTIMENT SCORE {token.symbol}" + "\n")
            file.write(str(sentiment_score))
            perplexity_result = perplexity_driver.chat_without_streaming(
                message=prompts.prompts.get("price_movements").get("msg") % (
                    token.symbol, full_token_name, token.twitter, datetime.now() - timedelta(days=7), datetime.now()),
                prompt=prompts.prompts.get("price_movements").get("perplexity_prompt") % (token.symbol, datetime.now() - timedelta(days=7), datetime.now())
            )
            file.write("=" * 100)
            file.write("\n" + f"PERPLEXITY {token.symbol}" + "\n")
            file.write(str(perplexity_result))
            llama_processing = llama.send_message(message=perplexity_result.removesuffix("</s>"),
                                                  prompt=prompts.prompts.get("price_movements").get("chatgpt_prompt"))
            file.write("=" * 100)
            file.write("\n" + f"LLAMA: {token.symbol}" + "\n")
            file.write(str(llama_processing))
            twitts_over_asset = await twitter_scraper.fetch_tweets(protocol_name=token.twitter.split("/")[-1])
            file.write("=" * 100)
            file.write("\n" + f"TWITS {token.symbol}" + "\n")
            file.write(str(twitts_over_asset))
            await asyncio.sleep(1800)