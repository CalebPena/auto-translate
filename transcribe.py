import os
import json
from itertools import chain
from google.api_core import client_options
from google.cloud.speech_v2 import (
    SpeechClient,
    StreamingRecognitionFeatures,
    StreamingRecognizeRequest,
    RecognitionConfig,
    AutoDetectDecodingConfig,
    StreamingRecognitionConfig,
)
from google.oauth2.service_account import Credentials
from dataclasses import dataclass

PROJECT_ID = "auto-translate-478321"

# Chirp 3
MODEL = "chirp_3"
REGION = "us"

# Chirp 2
# MODEL = "chirp_2"
# REGION = "us-central1"


def get_speech_client():
    credentials = os.getenv("GOOGLE_CREDENTIALS")

    if credentials is None:
        raise Exception("'GOOGLE_CREDENTIALS' not set")

    return SpeechClient(
        credentials=Credentials.from_service_account_info(json.loads(credentials)),
        client_options=client_options.ClientOptions(api_endpoint=f"{REGION}-speech.googleapis.com"),
    )


@dataclass
class Transcript:
    interm_text: str = ""
    final_text: str = ""

    def add_text(self, text: str, final: bool):
        self.interm_text = ""

        if final:
            self.final_text += text
        else:
            self.interm_text = text


def transcribe(audio_chunks, client: SpeechClient):
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
        for audio in audio_chunks
    )

    responses = client.streaming_recognize(requests=chain([config_request], audio_requests))

    transcript = Transcript()
    for response in responses:
        print(response)
        for result in response.results:
            transcript.add_text(result.alternatives[0].transcript, result.is_final)
            yield transcript
