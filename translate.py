from dataclasses import dataclass
import json
from typing import Generator
from openai import OpenAI
import os

from transcribe import Transcript

MODEL = "openai/gpt-oss-safeguard-20b:nitro"


def get_ai_client():
    credentials = os.getenv("OPEN_ROUTER_KEY")

    if credentials is None:
        raise Exception("'OPEN_ROUTER_KEY' not set")

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=credentials,
    )


@dataclass
class Translated:
    lang: str
    text: str


def p(*lines: str):
    return "\n".join(lines)


def kv(key: str, value: str):
    return p(f"<{key}>", value, f"</{key}>")


def system_prompt():
    return p(
        "The agent is a translator for a church.",
        "The agent's only goal is to provide accurate translations.",
        "The agent will recieve an input in the following format:",
        user_prompt(
            "Here is the text that was previously translated. Now you need to translate this text as well.",
            ["en", "es", "another_lang"],
            [
                Translated("en", "Here is the text that was previously translated."),
                Translated("es", "Aquí está el texto que fue traducido anteriormente."),
                Translated("another_lang", "..."),
            ],
        ),
        "",
        "And your responce should be in the following format as json:",
        json.dumps(
            {
                "translations": {
                    "en": "Here is the text that was previously translated. Now you need to translate this text as well.",
                    "es": "Aquí está el texto que fue traducido anteriormente. Ahora necesitas traducir este texto también.",
                    "another_lang": "...",
                }
            }
        ),
        "",
        "Additional instructions:",
        "1. The agent should translate to every language listed in <langs>.",
        "2. The agent should try to keep its translation as close to the previous response as possible",
        "but should feel empowered to change it if the underlying meaning has changed.",
        "3. The source language may change, and the agent should continue providing translations in all target languages listed in <langs>.",
        "4. The agent should only return valid json, that can be immediatly passed into JSON.stringify without causing an error.",
    )


def user_prompt(text: str, langs: list[str], prev_text: list[Translated]):
    langs = [kv("lang", l) for l in langs]
    prev = [kv("prev_translation", p(kv(t.lang, t.text))) for t in prev_text]

    return p(kv("langs", p(*langs)), kv("text", text), *prev)


def prompt(system: str, user: str, client: OpenAI):
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    res = completion.choices[0].message.content

    if res is None:
        raise Exception("response from AI was 'None'")

    return res


def translate(transcript: Generator[Transcript], langs: list[str], client: OpenAI):
    prev_translation = [Translated(l, "") for l in langs]

    system = system_prompt()

    for t in transcript:
        print(t, prev_translation)
        try:
            res = prompt(system, user_prompt(t.final_text + t.interm_text, langs, prev_translation), client)

            data = json.loads(res)
        except Exception as e:
            print("translation failed", repr(e))
            continue

        try:
            new_translation: list[Translated] = []
            for lang in langs:
                new_translation.append(
                    Translated(lang, data["translations"][lang]),
                )
        except KeyError:
            print(f"recieved invalid response from the AI. 'f{data}'")
            continue

        yield new_translation
        prev_translation = new_translation
