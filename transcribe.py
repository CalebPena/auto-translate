import os
import json
from threading import Thread
from itertools import chain
from queue import Queue
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions
from google.oauth2.service_account import Credentials


def get_speech_client():
    credentials = os.getenv("GOOGLE_CREDENTIALS")

    return SpeechClient(credentials=Credentials.from_service_account_info(json.loads(credentials)))


class Transcribe:
    def __init__(self, client: SpeechClient) -> None:
        self.client = client

        self._buff = Queue()
        self.closed = False

    def push(self, data):
        self._buff.put(data)

    def __enter__(self):
        self.closed = False
        return self

    def __exit__(self, *args, **kwargs):
        self.closed = True
        self._buff = Queue()

    def _generator(self):
        while not self.closed:
            next_data = self._buff.get()
            yield next_data

    def thread_transcribe(self):
        thread = Thread(target=self.transcribe)

        thread.start()

    def transcribe(self):
        recognition_config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=["en-us"],
            model="chirp_3",
        )
        streaming_config = cloud_speech.StreamingRecognitionConfig(config=recognition_config)
        config_request = cloud_speech.StreamingRecognizeRequest(streaming_config=streaming_config)

        audio_generator = self._generator()

        requests = (cloud_speech.StreamingRecognizeRequest(audio=audio) for audio in audio_generator)

        responses = self.client.streaming_recognize(requests=chain([config_request], requests))

        for response in responses:
            for result in response.results:
                print(result.alternatives[0].transcript)
