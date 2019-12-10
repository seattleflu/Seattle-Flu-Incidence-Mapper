import argparse
import csv
from logging import getLogger
import requests
import os
from tqdm import tqdm
from ratelimit import limits, RateLimitException
from backoff import on_exception, expo
logger = getLogger()


@on_exception(expo, RateLimitException, max_tries=8)
@limits(calls=2, period=1)
def upload_model(model, api_url, models_path, api_key, continue_on_error=False):
    headers = dict(Authorization=f'Bearer {api_key}')
    model_path = os.path.join(models_path, f"{model['filename']}.csv")
    model_data = {
        "id": model['filename'],
        "name": model['name'],
        "query_str": model['queryJSON'],
        "model_type": model['type'],
        "created": model['created']
    }
    try:
        files = {
            'model': (os.path.basename(model_path), open(model_path, 'rb'), 'text/plain')
        }
        r = requests.post(api_url, data=model_data, headers=headers, files=files)
        if r.status_code != 201 and not continue_on_error:
            logger.error(f"Failed to upload: {model['filename']}")
            raise Exception(f"upload failed of {model['filename']}: {r.status_code}: {r.content}")
        elif r.status_code != 201:
            logger.warning(f"Failed to upload: {model['filename']}: {r.status_code}: {r.content}")
    except FileNotFoundError as e:
        if not continue_on_error:
            raise e
        else:
            logger.warning(f"Could not find file from modelDB.tsv for {model['name']}")


def get_models(filename):
    with open(filename) as tsvfile:
        reader = csv.DictReader(tsvfile, dialect='excel-tab')
        rows = [row for row in reader]
    return rows


if __name__ == "__main__":

    default_model_store_path = os.path.abspath(os.path.join( os.path.os.getcwd(), 'test_model_store'))
    parser = argparse.ArgumentParser(description='Uploads trained SF Models to production')
    parser.add_argument("--db-file", default=os.path.join(default_model_store_path, "modelDB.tsv"),
                        help="Where the modelDB.tsv produced during training is stored")
    parser.add_argument("--model-store", default=default_model_store_path)
    parser.add_argument("--fail-on-error",dest='onerror', default=True, action='store_false',
                        help='Allows the procressing of files to continue even in the case of an error')
    parser.add_argument("--api-url", default="https://incidence-mapper.seattleflu.org//v1/generic_models",
                        help="URL for Seattle FLU API Incidence Mapper Model Server API")
    parser.add_argument("--api-key", help="API-KEY Allowing uploads")
    
    args = parser.parse_args()

    models = get_models(args.db_file)
    pbar = tqdm(models)
    for model in pbar:
        pbar.set_description(f"Processing {model['name']}")
        upload_model(model, args.api_url, args.model_store, args.api_key, args.onerror)
