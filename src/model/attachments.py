import base64
import re

import httpx


class AttachmentManager:
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.cache = {}

    async def get_bytes(self, url: str) -> tuple[bytes, str]:
        """
        Returns the bytes and content type of an attachment.
        """
        if url in self.cache:
            if "bytes" in self.cache[url]:
                bytes_ = self.cache[url]["bytes"]
            else:
                bytes_ = base64.b64decode(self.cache[url]["base64"])
                self.cache[url]["bytes"] = bytes_
            return bytes_, self.cache[url].get("content_type", None)
        if m := re.match(r"data:(.+);base64,(.+)", url):
            bytes_ = base64.b64decode(m.group(2))
            self.cache[url] = {
                "content_type": m.group(1),
                "bytes": bytes_,
                "base64": m.group(2),
            }
            return bytes_, m.group(1)
        elif m := re.match(r"data:(.+);charset=utf-8,(.+)", url):
            bytes_ = m.group(2).encode()
            self.cache[url] = {
                "content_type": m.group(1),
                "bytes": bytes_,
                "base64": m.group(2),
            }
            return bytes_, m.group(1)
        else:
            response = await self.client.get(url)
            content_type = response.headers.get("content-type", None)
            self.cache[url] = {
                "content_type": content_type,
                "bytes": response.content,
            }
            return response.content, content_type

    async def get_base64(self, url: str) -> tuple[str, str]:
        if url in self.cache:
            if "base64" in self.cache[url]:
                return self.cache[url]["base64"], self.cache[url]["content_type"]
            else:
                base64_content = base64.b64encode(self.cache[url]["bytes"]).decode()
                self.cache[url]["base64"] = base64_content
                return base64_content, self.cache[url]["content_type"]
        if m := re.match(r"data:(.+);(base64|charset=utf-8),(.+)", url):
            self.cache[url] = {
                "content_type": m.group(1),
                "base64": m.group(3),
            }
            return m.group(3), m.group(1)
        else:
            response = await self.client.get(url)
            content_type = response.headers.get("content-type", None)
            base64_content = base64.b64encode(response.content).decode()
            self.cache[url] = {
                "content_type": content_type,
                "bytes": response.content,
                "base64": base64_content,
            }
            return base64_content, content_type


attachment_manager = AttachmentManager()
