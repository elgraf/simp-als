#!/usr/bin/env python3

""" Feed fetcher """
import csv
import json
from datetime import datetime, timedelta, date
from traceback import format_exc, print_exc

from asyncio import (
    Semaphore,
    ensure_future,
    gather,
    get_event_loop,
    set_event_loop_policy,
    sleep
)

from aiohttp import ClientSession, BasicAuth, client
from uvloop import EventLoopPolicy
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure, DuplicateKeyError

from config import (
    CHECK_INTERVAL,
    DATABASE_NAME,
    MAX_CONCURRENT_REQUESTS,
    MONGO_SERVER,
    log,
    API_KEY,
    DETAILED_ADVERT,
    EXCHANGE_URL
)
from common import connect_redis, dequeue, retry

@retry(10, OperationFailure, 3)
async def do_update(collection, *args, **kwargs):
    collection.update_one(*args, **kwargs)


async def _get_exchange_rates(db, date_id):
    """Fetch rates"""
    rate = await db.rates.find_one({'date_id': date_id})
    log.info('Rate ID to found %s', date_id)
    if not rate:
        # no rate present, fetching
        async with client.request('GET', EXCHANGE_URL.format(date_id)) as response:
            body = await response.read()
            csv_body = body.decode('ascii', 'ignore').replace('\r', '').split('\n')

            if 'No data' in csv_body[0]:
                new_date_id = (date.today() - timedelta(1)).strftime("%d.%m.%Y")
                return await _get_exchange_rates(db, new_date_id)

            reader = csv.DictReader(csv_body, delimiter=';')
            for row in reader:
                if 'Euro' in row['Official exchange rate:']:
                    rate_value = row['']
                    rate = dict(**{
                        'date_id': date_id,
                        'type': 'Euro',
                        'value': rate_value.replace(',', '.')
                    })
                    try:
                        log.info('Inserting rate %s', rate)
                        await db.rates.insert_one(rate)
                        log.info('Added value %s', rate['value'])
                        return rate['value']
                    except Exception:
                        raise ValueError('Converting error')
    else:
        log.info('Found value %s', rate['value'])
        return rate['value']


async def get_exchange_rates(db):
    date_id = date.today().strftime("%d.%m.%Y")
    return await _get_exchange_rates(db, date_id)


async def fetch_one(session, feed, client, database, queue):
    """Fetch a detailed single advert"""
    advert_id = feed['advert_id']

    log.info("Fetching ID %s", advert_id)

    try:
        async with session.get(DETAILED_ADVERT.format(advert_id)) as response:
            body = await response.read()
            resp = body.decode('utf8')
            text = json.loads(resp)
            # TODO: check behavior for 301/302
            if not await database.adverts.find_one({'advert_id': advert_id}):
                # no detailed advert with these id
                log.info("Inserting %s" % advert_id)
                # converting
                if 'eur' in text['price']['unit']:
                    text['price']['unit'] = 'mdl'
                    current_exchange_rate = await get_exchange_rates(database)
                    text['price']['value'] = round(int(text['price']['value']) * float(current_exchange_rate))

                advert = dict(**{
                    'advert_id': advert_id,
                    'created': datetime.now(),
                    'last_fetched': datetime(1970, 1, 1),
                    'content': text
                })
                log.info('Advert for inserting %s', advert)
                try:
                    inserted = await database.adverts.insert_one(advert)
                    log.info("Inserted advert is %s", inserted)
                    return advert, response.status
                except DuplicateKeyError as e:
                    log.info("Advert already exist")
                except Exception as e:
                    log.error(e)
            else:
                found_advert = await database.adverts.find_one({'advert_id': advert_id})
                print('advert found', found_advert)
                update = {
                    'last_status': response.status,
                    'last_fetched': datetime.now(),
                }

                await do_update(database.adverts, {'advert_id': advert_id}, {'$set': update})
                return found_advert, response.status

    except Exception as e:
        print_exc()
        return advert, 0


async def throttle(sem, session, feed, client, database, queue):
    """Throttle number of simultaneous requests"""

    async with sem:
        res = await fetch_one(session, feed, client, database, queue)
        log.info("%s: %d", res, res[1])


async def feed_fetcher(database):
    """Fetch all the feeds"""

    client = ClientSession(auth=BasicAuth(API_KEY))
    sem = Semaphore(MAX_CONCURRENT_REQUESTS)

    queue = await connect_redis()
    while True:
        log.info("Beginning run.")
        tasks = []
        async with client as session:
            while True:
                try:
                    job = await dequeue(queue, 'fetcher')
                    feed = await database.feeds.find_one({'advert_id': job['_id']})
                    task = ensure_future(throttle(sem, session, feed, client, database, queue))
                    tasks.append(task)
                except Exception:
                    log.error(format_exc())
                    break
            responses = gather(*tasks)
            await responses
            log.info("Run complete, sleeping %ds...", CHECK_INTERVAL)
            await sleep(1)
    queue.close()
    await queue.wait_closed()


def main():
    """Setup coroutines and kickstart fetcher"""
    set_event_loop_policy(EventLoopPolicy())

    motor = AsyncIOMotorClient(MONGO_SERVER)
    database = motor[DATABASE_NAME]

    loop = get_event_loop()
    ensure_future(feed_fetcher(database))
    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    main()
