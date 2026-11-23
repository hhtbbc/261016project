"""One bounded replay of same ESA URLs after transport timeouts; never changes source."""
from pathlib import Path
import json
from time import monotonic, process_time
import resource

from fetch_summer_assets_v38 import OUT, RAW, OLD, DAYS, save, history_pins, Meter, bounded_get


def main():
    wall,cpu=monotonic(),process_time()
    history_pins()
    old=json.loads((OUT/'download_manifest.json').read_bytes())
    dates=json.loads((OLD/'acquisition_gaps.json').read_bytes())['by_date'][:2]
    meter=Meter()
    meter.rx.update(old['network']['received_transport_bytes'])
    meter.tx.update(old['network']['sent_transport_bytes'])
    meter.reserved_failed_tx.update(old['network']['conservative_failed_send_reservations'])
    save('ESA_retry_once.json',dict(scope='same official URLs only on pre-response timeout',dates=DAYS))
    obtained={}
    for row in dates:
        day=row['date']
        key='Swarm_'+day
        prior=json.loads((OUT/(key+'_http.json')).read_text())['requests']
        item=row['observation']
        url=item['historical_index_URL']
        if key in old['assets'] or len(prior)!=1 or prior[0]['HTTP'] is not None or prior[0].get('error_type')!='TimeoutError':
            continue
        assert prior[0]['original_URL']==url
        trace=[]
        try:
            obtained[key]=bounded_get(url,RAW/item['product'],meter,'small',trace,
                expected_bytes=item['historical_index_bytes'],magic=(b'PK\x03\x04',),max_body=2**20)
            print(key,obtained[key]['HTTP'],obtained[key]['bytes'],flush=True)
        except (ValueError,OSError,EOFError) as exc:
            print(key,'FAILED',str(exc),flush=True)
        finally:
            save(key+'_retry_http.json',dict(key=key,requests=trace))
    save('ESA_retry_manifest.json',dict(assets=obtained,network_cumulative=meter.summary(),
            wall_s=monotonic()-wall,CPU_s=process_time()-cpu,
            peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    main()
