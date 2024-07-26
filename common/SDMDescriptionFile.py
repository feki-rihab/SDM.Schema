from requests import get
from requests.exceptions import HTTPError, RequestException, ReadTimeout, ConnectionError
from json.decoder import JSONDecodeError
from os.path import join, dirname
from threading import Thread, Condition, Event
from datetime import datetime, timedelta
import logging


class SDMDescriptionFile:
    def __init__(self, logger=None):
        # Official file with all the information of the Data Models
        self.official_list_data_models = ('https://raw.githubusercontent.com/smart-data-models/data-models/master/'
                                          'specs/AllSubjects/official_list_data_models.json')
        self.official_list_data_models_data = dict()

        self.data_models_metadata = 'https://smartdatamodels.org/extra/datamodels_metadata.json'
        self.data_models_metadata_data = dict()

        filename = join(dirname(dirname(__file__)), 'logs', 'app.log')

        if logger is None:
            logging.basicConfig(filename=filename,
                                filemode='w',
                                format='%(name)s - %(levelname)s - %(message)s',
                                level=logging.DEBUG)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.check_interval_minutes = 720  # 12h * 60m
        self.obtained_time = datetime.now()

        # Create a Condition object
        self.data_available = Condition()

        # Start the background thread
        self.background_thread = Thread(target=self.get_files_background)
        self.background_thread.start()
        self._kill = Event()

    def get_files_background(self):
        while True:
            current_time = datetime.now()

            if len(self.data_models_metadata_data) == 0 or (current_time - self.obtained_time) > timedelta(days=7):
                self.official_list_data_models_data = self.__get_data__(url=self.official_list_data_models)
                self.data_models_metadata_data = self.__get_data__(url=self.data_models_metadata)

                self.obtained_time = datetime.now()

                self.logger.info("Download complete!")
                elapsed_time = self.obtained_time - current_time
                self.logger.info(f"Total time: {elapsed_time.total_seconds():.2f} seconds")

            with self.data_available:
                self.data_available.notify()

            # Sleep for the specified interval, in seconds
            # sleep(self.check_interval_minutes * 60)

            # If no kill signal is set, sleep for the interval,
            # If kill signal comes in while sleeping, immediately
            #  wake up and handle
            is_killed = self._kill.wait(self.check_interval_minutes * 60)
            if is_killed:
                break

        self.logger.info("Stopping Thread...")


    @staticmethod
    def __get_data__(url: str) -> dict:
        response = None

        try:
            response = get(url=url, timeout=1)
            response.raise_for_status()
        except HTTPError as errh:
            print("HTTP Error")
            print(errh.args[0])
        except ConnectionError as conerr:
            print("Connection error")
            print(conerr)
        except RequestException as errex:
            print("Exception request")
            print(errex)
        except ReadTimeout as errrt:
            print("Time out")
            print(errrt)

        try:
            response = response.json()
        except JSONDecodeError as e:
            print("JSONDecodeError")
            print(e)

        return response

    def get_data(self, entity_name: str) -> dict:
        """
        Get the link to the repository and the link to the raw data of the model.yaml of the corresponding Data Model
        :param entity_name: The name of the entity to search the links in GitHub
        :return:
        """
        self.logger.info(f"Requesting links from entity '{entity_name}'")

        # Acquire the lock associated with the Condition
        with self.data_available:
            # Wait until data is available
            while self.official_list_data_models_data == dict():
                self.data_available.wait()

        data_model_metadata = \
            [x for x in self.data_models_metadata_data if x['dataModel'] == entity_name]

        official_data_model = \
            [x for x in self.official_list_data_models_data['officialList'] if entity_name in x['dataModels']]

        entity_repo_link = official_data_model[0]['repoLink']
        entity_repo_link = entity_repo_link.replace('.git', '')
        entity_repo_link = join(entity_repo_link, 'tree', 'master', entity_name)

        entity_yaml_link = data_model_metadata[0]['yamlUrl']
        entity_jsonschema_url = data_model_metadata[0]['jsonSchemaUrl']

        response = {
            'repo': entity_repo_link,
            'yaml': entity_yaml_link,
            'jsonSchema': entity_jsonschema_url
        }

        return response

    def stop(self):
        """
        Send the message to stop the thread
        """
        self._kill.set()


if __name__ == '__main__':
    sdm_links = SDMDescriptionFile()
    response = sdm_links.get_data(entity_name='WeatherObserved')

    print(f"Repository link: {response['repo']}")
    print(f"Yaml link: {response['yaml']}")
    print(f"JSONSchema link: {response['jsonSchema']}")
