# simp-als
Simpals. All is simple :)

## What

An attempt to pass simpals test task (scrapping 999 user adverts api and stocking them into db + index all data in 
elasticearch in realtime :).

## How
* I decided I wanted this to be fully distributed, so I split the logic into several worker processes who coordinate via [Redis][redis] queues, orchestrated using `docker-compose`
* I decided to take a ride on the bleeding edge and refactored everything to use from tornado to `asyncio/uvloop`
* Rather than just convert EU to MDL everytime , I also decided to stock all BNM rates into mongodb
* To index all needed data live into Elasticsearch, I used monstache. The main dependency is to run mongodb as replica( I decided to simply convert standalone mongodb server into replica mode) 


## ToDo

* [ ] Add web interface for metrics
* [ ] Add unit tests
* [ ] Add integration tests

### Architecture

* [x] `import.py` is a raw adverts importer
* [ ] `metrics.py` keeps tabs on various stats and pushes them out every few seconds 
* [x] `fetcher.py` fetches adverts, convert all needed data and stores them on MongoDB
* [ ] `web.py` provides a simple web front-end for live status updates via SSE.

Processes are written to leverage `asyncio/uvloop` and interact via [Redis][redis] 

A Docker compose file is supplied for running the entire stack locally.

[redis]: http://redis.io
[aiohttp]: https://aiohttp.readthedocs.io/en/stable/
[elasticsearch]: https://www.elastic.co/
[monstache]: https://github.com/rwynn/monstache

## Development


### :construction: Steps to launch the development environment:
1. `docker-compose up --no-start && docker-compose start`
2. `docker-compose ps`
3. `Find specific container name for db ( for example, simp_als_db_1)`
4. `docker exec -it $name_of_container_found_in_step_3 mongo`
5. `rs.initate()`



### :globe_with_meridians: Steps to verify elastic indexes:
1. ` curl -X GET "localhost:9200/_cat/nodes?v&pretty"`


### :squirrel: Database management
Connect to mongo-database:
```bash
docker exec -it simp-als_db_1 mongo
Use desired query :))
```
