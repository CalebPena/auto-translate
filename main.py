from websockets.sync.server import ServerConnection, serve
from transcribe import get_speech_client, Transcribe
from dotenv import load_dotenv

load_dotenv()

speech_client = get_speech_client()


def echo(websocket: ServerConnection):
    with Transcribe(speech_client) as transcribe:
        transcribe.thread_transcribe()
        for message in websocket:
            transcribe.push(message)


def main():
    with serve(echo, "localhost", 8765) as server:
        print("Server Starting")
        server.serve_forever()


if __name__ == "__main__":
    main()
