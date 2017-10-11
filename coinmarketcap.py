from elasticsearch import Elasticsearch
from time import sleep
import logging
import requests
import json
import sys
from coinmarketcap_utils import *

import settings

def main():

    logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s',level=settings.LOGLEVEL)
    es = Elasticsearch(settings.ELASTICSEARCH_CONNECT_STRING)
    es_indexname = "cmc_v1"


    logging.info('Market Refresh Rate: ' + str(settings.MARKET_REFRESH_RATE) + ' seconds.')

    logging.info('Application Started.')

    try:
        mapping = {
            "ticker": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "last_updated": {"type": "date"},
                    "rank": {"type": "double"},
                    "price_usd": {"type": "double"},
                    "price_btc": {"type": "double"},
                    "24h_volume_usd": {"type": "double"},
                    "market_cap_usd": {"type": "double"},
                    "available_supply": {"type": "double"},
                    "total_supply": {"type": "double"},

                    "percent_change_1h": {"type": "double"},
                    "percent_change_24h": {"type": "double"},
                    "percent_change_7d": {"type": "double"},

                    "percent_change_1h_to_btc": {"type": "double"},
                    "percent_change_24h_to_btc": {"type": "double"},
                    "percent_change_7d_to_btc": {"type": "double"},

                    "percent_change_1h_to_gmc": {"type": "double"},
                    "percent_change_24h_to_gmc": {"type": "double"},
                    "percent_change_7d_to_gmc": {"type": "double"},

                    "price_usd_derivative": {"type": "double"},
                    "price_btc_derivative": {"type": "double"},

                    "percent_change_1h_derivative": {"type": "double"},
                    "percent_change_24h_derivative": {"type": "double"},
                    "percent_change_7d_derivative": {"type": "double"},

                    "percent_change_1h_to_btc_derivative": {"type": "double"},
                    "percent_change_24h_to_btc_derivative": {"type": "double"},
                    "percent_change_7d_to_btc_derivative": {"type": "double"},

                    "percent_change_1h_to_gmc_derivative": {"type": "double"},
                    "percent_change_24h_to_gmc_derivative": {"type": "double"},
                    "percent_change_7d_to_gmc_derivative": {"type": "double"},

                    "percent_change_1h_magnitude": {"type": "double"},
                    "percent_change_24h_magnitude": {"type": "double"},
                    "percent_change_7d_magnitude": {"type": "double"},

                    "percent_change_1h_to_btc_magnitude": {"type": "double"},
                    "percent_change_24h_to_btc_magnitude": {"type": "double"},
                    "percent_change_7d_to_btc_magnitude": {"type": "double"},

                    "percent_change_1h_to_gmc_magnitude": {"type": "double"},
                    "percent_change_24h_to_gmc_magnitude": {"type": "double"},
                    "percent_change_7d_to_gmc_magnitude": {"type": "double"}
                }
            }
        }

        # try:
        #     es.indices.delete(es_indexname)
        # except:
        #     pass
        es.indices.create(es_indexname)
        es.indices.put_mapping(index=es_indexname, doc_type="ticker", body=mapping)

    except:
        logging.warning("Index problem: " + str(sys.exc_info()[0]))
        # raise

    agg = Aggregations()

    #Record Ticks
    while True:
        try:
            # get ticker for all currencies
            r = requests.get("https://api.coinmarketcap.com/v1/ticker/")
            jsond = json.loads(r.content)

            # calculate the global market cap change
            gmc_before_1h = 0
            gmc_before_24h = 0
            gmc_before_7d = 0
            gmc_now = 0

            utcnow = datetime.utcnow()

            for e in jsond:
                # now-before / before = now/before - 1 = now_diff
                # => now / before = now_diff+1
                # => before = now / now_diff+1
                now_diff_1h  = make_float(e['percent_change_1h'])  / 100
                now_diff_24h = make_float(e['percent_change_24h']) / 100
                now_diff_7d  = make_float(e['percent_change_7d'])  / 100
                now = make_float(e['market_cap_usd'])

                before_1h  = now  / (now_diff_1h + 1)
                before_24h = now  / (now_diff_24h + 1)
                before_7d  = now  / (now_diff_7d + 1)

                gmc_now += now
                gmc_before_1h += before_1h
                gmc_before_24h += before_24h
                gmc_before_7d += before_7d

            # base of division is the "before" mc, because from 1 to 2 is 100% increase.
            # Otherwise from 1 to 2 will be 50% increase, 1 to 3 will be 66% increase, etc.. ( 3 - 1 / 3 = 0.66 )
            gmc_percent_change_1h   = ( gmc_now / gmc_before_1h - 1 ) * 100
            gmc_percent_change_24h  = ( gmc_now / gmc_before_24h - 1 ) * 100
            gmc_percent_change_7d   = ( gmc_now / gmc_before_7d - 1 ) * 100

            btc_percent_change_1h   = make_float(jsond[0]['percent_change_1h'])
            btc_percent_change_24h  = make_float(jsond[0]['percent_change_24h'])
            btc_percent_change_7d   = make_float(jsond[0]['percent_change_7d'])

            for e in jsond:
                e['@timestamp'] = utcnow
                e['last_updated'] = int(e['last_updated']) * 1000 \
                    if e['last_updated'] is not None else None
                transformed = transform_for_elastic(e,
                                                    btc_percent_change_1h,
                                                    btc_percent_change_24h,
                                                    btc_percent_change_7d,
                                                    gmc_percent_change_1h,
                                                    gmc_percent_change_24h,
                                                    gmc_percent_change_7d)
                # rank metrics
                transformed = agg.add_min_for_property(transformed, "rank", 1000)
                transformed = agg.add_max_for_property(transformed, "rank", 1000)

                deepness = str(200)
                transformed = agg.add_avg_for_property(transformed,     "rank", deepness)
                transformed = agg.add_min_for_property(transformed,     "rank_avg"+deepness, deepness)
                transformed = agg.add_ceil_for_property(transformed,    "rank_avg"+deepness+"_min"+deepness)
                transformed = agg.add_floor_for_property(transformed,   "rank_avg"+deepness+"_min"+deepness)
                transformed = agg.add_max_for_property(transformed,     "rank_avg"+deepness, deepness)
                transformed = agg.add_ceil_for_property(transformed,    "rank_avg"+deepness+"_max"+deepness)
                transformed = agg.add_floor_for_property(transformed,   "rank_avg"+deepness+"_max"+deepness)
                transformed = agg.add_avg_for_property(transformed,     "price_btc", deepness)
                transformed = agg.add_avg_for_property(transformed,     "price_usd", deepness)
                transformed = agg.add_avg_for_property(transformed,     "market_cap_usd", deepness)
                transformed = agg.add_avg_for_property(transformed,     "market_cap_btc", deepness)

                deepness = str(1000)
                transformed = agg.add_avg_for_property(transformed, "rank", deepness)
                transformed = agg.add_min_for_property(transformed, "rank_avg" + deepness, deepness)
                transformed = agg.add_ceil_for_property(transformed, "rank_avg" + deepness + "_min" + deepness)
                transformed = agg.add_floor_for_property(transformed, "rank_avg" + deepness + "_min" + deepness)
                transformed = agg.add_max_for_property(transformed, "rank_avg" + deepness, deepness)
                transformed = agg.add_ceil_for_property(transformed, "rank_avg" + deepness + "_max" + deepness)
                transformed = agg.add_floor_for_property(transformed, "rank_avg" + deepness + "_max" + deepness)
                transformed = agg.add_avg_for_property(transformed, "volume_percent_of_market_cap", deepness)
                transformed = agg.add_avg_for_property(transformed, "price_btc", deepness)
                transformed = agg.add_avg_for_property(transformed, "price_usd", deepness)
                transformed = agg.add_avg_for_property(transformed, "market_cap_usd", deepness)
                transformed = agg.add_avg_for_property(transformed, "market_cap_btc", deepness)

                es.index(index=es_indexname, doc_type="ticker", body=transformed)

            logging.info("Prises imported")

            sleep(settings.MARKET_REFRESH_RATE)

        except Exception as e:
            logging.error(e)
            sleep(settings.RETRY_RATE)

if __name__ == '__main__':
    main()
