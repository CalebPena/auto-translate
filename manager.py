import json
from threading import Thread
from queue import Queue

from google.cloud.speech_v2 import SpeechClient
from openai import OpenAI
from websockets.sync.server import ServerConnection

from transcribe import transcribe
from translate import translate


class Manager:
    def __init__(self, speech_client: SpeechClient, ai_client: OpenAI, socket: ServerConnection) -> None:
        self._buff = Queue()
        self.closed = False

        self._speech_client = speech_client
        self._ai_client = ai_client
        self._socket = socket

        self.langs = ["en", "es", "ar"]

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
            next_data = self._buff.get(block=True)
            yield next_data

    def run(self):
        thread = Thread(target=self._flow)

        thread.start()

    def _flow(self):
        transcripts = transcribe(self._generator(), self._speech_client)
        translations = translate(transcripts, self.langs, self._ai_client)

        for translation in translations:
            data = json.dumps({"translations": {t.lang: t.text for t in translation}})
            print(data)
            self._socket.send(data)
