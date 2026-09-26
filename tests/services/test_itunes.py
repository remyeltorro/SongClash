from songclash.services import itunes


def test_itunes_preview_matching(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "artistName": "Other",
                        "trackName": "Creep",
                        "collectionName": "X",
                        "previewUrl": "wrong",
                    },
                    {
                        "artistName": "Radiohead",
                        "trackName": "Creep",
                        "collectionName": "Live",
                        "previewUrl": "ok",
                    },
                    {
                        "artistName": "Radiohead",
                        "trackName": "Creep",
                        "collectionName": "Pablo Honey",
                        "previewUrl": "best",
                    },
                ]
            }

    monkeypatch.setattr(itunes.requests, "get", lambda *a, **k: Resp())
    assert itunes.find_preview("Radiohead", "Creep", "Pablo Honey (1993)") == "best"
    assert itunes.find_preview("Radiohead", "Creep (Acoustic)", "Pablo Honey (1993)") == "best"
    assert itunes.find_preview("Radiohead", "Creep", "") == "ok"
    assert itunes.find_preview("Radiohead", "Karma Police", "") == ""


def test_itunes_retries_without_bracketed_part(monkeypatch):
    terms = []

    class Resp:
        def __init__(self, term):
            self.term = term

        def raise_for_status(self):
            pass

        def json(self):
            if "(" in self.term:
                return {"results": []}
            return {"results": [{"artistName": "Radiohead", "trackName": "Backdrifts", "previewUrl": "url"}]}

    def fake_get(url, params, timeout):
        terms.append(params["term"])
        return Resp(params["term"])

    monkeypatch.setattr(itunes.requests, "get", fake_get)
    assert itunes.find_preview("Radiohead", "Backdrifts. (Honeymoon Is Over.)") == "url"
    assert terms == ["Radiohead Backdrifts. (Honeymoon Is Over.)", "Radiohead Backdrifts"]
