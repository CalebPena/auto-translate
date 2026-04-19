import os
import json
from threading import Thread
from itertools import chain
from queue import Queue
from google.api_core import client_options
from google.cloud.speech_v2 import (
    SpeechClient,
    StreamingRecognitionFeatures,
    StreamingRecognizeRequest,
    RecognitionConfig,
    AutoDetectDecodingConfig,
    StreamingRecognitionConfig,
    TranslationConfig,
)
from google.oauth2.service_account import Credentials

PROJECT_ID = "auto-translate-478321"

# Chirp 3
MODEL = "chirp_3"
REGION = "us"

# Chirp 2
# MODEL = "chirp_2"
# REGION = "us-central1"


def get_speech_client():
    credentials = os.getenv("GOOGLE_CREDENTIALS") or ""

    return SpeechClient(
        credentials=Credentials.from_service_account_info(json.loads(credentials)),
        client_options=client_options.ClientOptions(api_endpoint=f"{REGION}-speech.googleapis.com"),
    )


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
        recognition_config = RecognitionConfig(
            auto_decoding_config=AutoDetectDecodingConfig(),
            language_codes=["en-US"],
            model=MODEL,
        )
        streaming_config = StreamingRecognitionConfig(
            config=recognition_config,
            streaming_features=StreamingRecognitionFeatures(interim_results=True),
        )
        config_request = StreamingRecognizeRequest(
            recognizer=f"projects/{PROJECT_ID}/locations/{REGION}/recognizers/_",
            streaming_config=streaming_config,
        )

        audio_requests = (
            StreamingRecognizeRequest(
                audio=audio,
            )
            for audio in self._generator()
        )

        responses = self.client.streaming_recognize(requests=chain([config_request], audio_requests))

        for response in responses:
            print(response)
            for result in response.results:
                if result.is_final:
                    print(result.alternatives[0].transcript)
