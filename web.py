#!/bin/env python3

""" Web server """
from multiprocessing import cpu_count

from motor.motor_asyncio import AsyncIOMotorClient
from sanic import Sanic
from sanic.response import json

from config import (
    BIND_ADDRESS,
    DATABASE_NAME,
    HTTP_PORT,
    MONGO_SERVER,
    log
)
from sanic_paginate import Pagination

app = Sanic(__name__)

db = None


@app.route('/adverts/', methods=['GET'])
@app.route('/adverts/<advert_id>', methods=['GET'])
async def adverts(req, advert_id=None):
    """Paged navigation of adverts using aiocache to lessen database hits."""

    page, per_page, offset = Pagination.get_page_args(req)

    # hide system fields
    fields = {'_id': 0, 'checksum': 0, 'created': 0, 'last_fetched': 0}
    if advert_id:
        data = await db.adverts.find({'advert_id': advert_id}, fields).skip(offset).to_list(per_page)
        total = len(data)

    else:
        data = await db.adverts.find({}, fields).skip(offset).to_list(per_page)
        total = len(data)
    pagination = Pagination(req, total=total, data=data)
    return json(pagination)


@app.route('/raw_adverts/', methods=['GET'])
@app.route('/raw_adverts/<advert_id>', methods=['GET'])
async def raw_adverts(req, advert_id=None):
    """ Paged navigation of raw_adverts - using aiocache to lessen database hits. """

    page, per_page, offset = Pagination.get_page_args(req)

    # hide system fields
    fields = {'_id': 0, 'checksum': 0, 'created': 0, 'last_fetched': 0}
    if advert_id:
        data = await db.feeds.find({'advert_id': advert_id}, fields).skip(offset).to_list(per_page)
        total = len(data)
    else:
        data = await db.feeds.find({}, fields).skip(offset).to_list(per_page)
        total = len(data)
    pagination = Pagination(req, total=total, data=data)
    return json(pagination)


@app.listener('after_server_start')
async def init_connections(sanic, loop):
    """Bind the database to Sanic's event loop."""

    global db
    motor = AsyncIOMotorClient(MONGO_SERVER, io_loop=loop)
    db = motor[DATABASE_NAME]


if __name__ == '__main__':
    log.debug("Beginning run.")
    app.run(host=BIND_ADDRESS, port=HTTP_PORT, workers=cpu_count(), debug=True)
