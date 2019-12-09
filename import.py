#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import math
from hashlib import sha1
from datetime import datetime, timedelta

from asyncio import (
    ensure_future,
    get_event_loop,
    set_event_loop_policy,
    sleep
)
from aiohttp import ClientSession, BasicAuth
from uvloop import EventLoopPolicy
from pymongo.errors import DuplicateKeyError, OperationFailure
from motor.motor_asyncio import AsyncIOMotorClient

from common import retry, enqueue, connect_redis
from config import (
    DATABASE_NAME,
    FETCH_INTERVAL,
    API_KEY,
    ALL_ADVERTS_URL,
    log,
    MONGO_SERVER
)

@retry(10, OperationFailure, 3)
async def do_update(collection, *args, **kwargs):
    collection.update_one(*args, **kwargs)


async def create_database(db):
    await db.rates.create_index("date_id", unique=True)
    await db.feeds.create_index("advert_id", unique=True)
    await db.adverts.create_index("advert_id", unique=True)


async def generate_requests(db):
    client = ClientSession(auth=BasicAuth(API_KEY))
    while True:
        try:
            async with client.get(ALL_ADVERTS_URL.format(1)) as response:
                text = json.loads(await response.text())
                log.info('Total adverts for page is %s', text['total'])
                total = int(text['total'])
                for page in range(1, math.ceil(total / 100) + 1):
                    await update_database(db, client, page)
        except Exception as e:
            log.error(e)
        await sleep(FETCH_INTERVAL)


async def update_database(db, client, page):
    """Import raw adverts from getAdverts"""
    queue = await connect_redis()
    feeds = db.feeds
    # TODO: turn this into a bulk upsert
    try:
        log.info('Requesting page %s', page)
        async with client.get(ALL_ADVERTS_URL.format(page)) as response:
            body = await response.read()
            resp = body.decode('utf8')
            text = json.loads(resp)
            threshold = datetime.now() - timedelta(seconds=FETCH_INTERVAL)

            for advert in text['adverts']:
                advert_id = advert['id']
                if not await feeds.find_one({'advert_id': advert_id}):
                    # no feed with these id found, creating
                    log.info("Inserting %s" % advert_id)
                    feed = dict(**{
                        'advert_id': advert_id,
                        'checksum': sha1(resp.encode('utf-8')).hexdigest(),
                        'created': datetime.now(),
                        'last_fetched': datetime(1970, 1, 1),
                        'content': advert,
                        'last_status': response.status
                    })
                    try:
                        inserted = await feeds.insert_one(feed)
                        log.info("Inserted feed is %s", inserted)
                        await enqueue(queue, "fetcher", {
                            "_id": advert_id,
                            "scheduled_at": datetime.now()
                        })
                    except DuplicateKeyError as e:
                        log.error("Feed already exist")
                    except Exception as e:
                        log.error(e)

                else:
                    found_feed = await feeds.find_one({'advert_id': advert_id})
                    log.info('Feed found %s', found_feed)
                    last_fetched = found_feed.get('last_fetched', threshold)
                    update = {
                        'last_status': response.status
                    }
                    current_checksum = sha1(resp.encode('utf-8')).hexdigest()

                    if found_feed['checksum'] != current_checksum:
                        update['content'] = advert
                        update['checksum'] = current_checksum
                        update['last_fetched'] = datetime.now()
                        await enqueue(queue, "fetcher", {
                            "_id": advert_id,
                            "scheduled_at": datetime.now()
                        })

                    if last_fetched <= threshold:
                        update['last_fetched'] = datetime.now()
                        await enqueue(queue, "fetcher", {
                            "_id": advert_id,
                            "scheduled_at": datetime.now()
                        })
                    await do_update(db.feeds, {'advert_id': advert_id}, {'$set': update})

    except Exception as e:
        log.error(e)
    queue.close()
    await queue.wait_closed()
    log.info("Run complete")

if __name__ == '__main__':

    set_event_loop_policy(EventLoopPolicy())
    loop = get_event_loop()

    c = AsyncIOMotorClient(MONGO_SERVER)
    db = c[DATABASE_NAME]
    
    ensure_future(create_database(db))
    ensure_future(generate_requests(db))

    try:
        loop.run_forever()
    finally:
        loop.close()
