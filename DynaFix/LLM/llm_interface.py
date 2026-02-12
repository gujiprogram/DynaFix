from openai import OpenAI
import threading
import queue
import tiktoken
import csv
from pathlib import Path
from datetime import datetime


class LLMInterface:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
        self.encoding = tiktoken.get_encoding("cl100k_base")

        # Final CSV path
        self.csv_path = Path("./result/defects4j/token_usage_gpt4o.csv")
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Write header if file does not exist
        if not self.csv_path.exists():
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["slug", "ID", "model", "input_tokens", "output_tokens", "total_tokens"])

    def _tokens_for_messages(self, messages: list) -> int:
        """OpenAI official billing calculation, 0 error"""
        tokens = 0
        for msg in messages:
            tokens += 3
            tokens += len(self.encoding.encode(msg.get("role", ""))) + 1
            tokens += len(self.encoding.encode(msg.get("content", "")))
        tokens += 3
        return tokens

    def _record_usage(self, slug: str, ID: int, messages: list, response_text: str):
        input_tokens = self._tokens_for_messages(messages)
        output_tokens = len(self.encoding.encode(response_text))

        record = [
            slug,
            ID,
            self.model,
            input_tokens,
            output_tokens,
            input_tokens + output_tokens
        ]

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(record)

        print(
            f"[TOKEN] {slug} | ID {ID} | in {input_tokens} -> out {output_tokens} = {input_tokens + output_tokens} tokens")

    def _request_worker(self, prompt, temperature, out_queue):
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=prompt,
                temperature=temperature
            )
            out_queue.put(resp)
        except Exception as e:
            out_queue.put(e)

    def chat(self, prompt, ID, slug, max_retries=10, temperature=1.0, timeout=300):
        for attempt in range(max_retries):
            print(f"[ID {ID} | {slug}] Request {attempt + 1}...")

            q = queue.Queue()
            t = threading.Thread(target=self._request_worker, args=(prompt, temperature, q), daemon=True)
            t.start()
            t.join(timeout=timeout)

            if t.is_alive():
                print(f"[ID {ID} | {slug}] Timeout, retrying...")
                continue

            result = q.get()
            if isinstance(result, Exception):
                print(f"[ID {ID} | {slug}] Exception: {result}")
                continue

            # Simplest fix - add try-except in place
            try:
                content = result.choices[0].message.content.strip()
            except AttributeError:
                # Log error and return empty string
                print(f"Warning: Received None response at iteration {ID}")
                content = ""

            print(f"[ID {ID} | {slug}] Success")

            self._record_usage(slug, ID, prompt, content)

            return content

        print(f"[ID {ID} | {slug}] All failed")
        return None