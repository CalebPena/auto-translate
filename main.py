from websockets.sync.server import ServerConnection, serve
from transcribe import get_speech_client
from translate import get_ai_client
from manager import Manager
from dotenv import load_dotenv

load_dotenv()

speech_client = get_speech_client()
ai_client = get_ai_client()


def echo(websocket: ServerConnection):
    with Manager(speech_client, ai_client) as manager:
        manager.run()
        for message in websocket:
            manager.push(message)


def main():
    with serve(echo, "localhost", 8765) as server:
        print("Server Starting")
        server.serve_forever()


if __name__ == "__main__":
    main()
