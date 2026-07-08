"""Smoke test: run one extraction end to end against a stub AI provider.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/run_once.py)
"""
from ai.bedrock_provider import BedrockProvider
from worker.ai_extract import extract_candidate


def main():
    ai = BedrockProvider(client=None, model_id="stub")
    text = """
    TONIGHT @ Mohawk Austin
    Doors 7pm / Show 8pm
    Artist: Example Band
    Tickets: https://example.com/tickets
    """
    cid = extract_candidate(
        ai=ai,
        text=text,
        source_class="social",
        source_name="manual_test",
        source_url="https://example.com/post",
        sxsw_mode=False
    )
    print({"candidate_id": cid})


if __name__ == "__main__":
    main()
