import json
import hashlib

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# ---------------------------------------------------------------------------
# OpenTelemetry setup — configure once, export every span to Jaeger via OTLP
# ---------------------------------------------------------------------------
resource = Resource.create({"service.name": "trust-score-calculator"})
provider = TracerProvider(resource=resource)

# Jaeger's all-in-one image accepts OTLP gRPC on port 4317 by default
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

trace.set_tracer_provider(provider)
tracer = trace.get_tracer("trust_score_calculator")

# ---------------------------------------------------------------------------
# Input Scores
# ---------------------------------------------------------------------------
scores = {
    "accuracy": 95,
    "fairness": 60,
    "security": 92,
    "compliance": 95
}

# Weights
weights = {
    "accuracy": 0.30,
    "fairness": 0.25,
    "security": 0.25,
    "compliance": 0.20
}


def validate_input(scores, weights):
    with tracer.start_as_current_span("validate_input") as span:
        span.set_attribute("input.score_keys", list(scores.keys()))
        span.set_attribute("input.weight_keys", list(weights.keys()))

        weight_sum = round(sum(weights.values()), 4)
        span.set_attribute("input.weight_sum", weight_sum)

        is_valid = set(scores.keys()) == set(weights.keys()) and weight_sum == 1.0
        span.set_attribute("input.is_valid", is_valid)

        if not is_valid:
            span.set_attribute("input.validation_error", True)
            raise ValueError("Scores and weights are misaligned or weights don't sum to 1.0")

        return is_valid


def calculate_trust_score(scores, weights):
    with tracer.start_as_current_span("calculate_trust_score") as span:
        trust_score = 0

        for attribute in scores:
            contribution = scores[attribute] * weights[attribute]
            trust_score += contribution
            # per-attribute contribution recorded as its own span attribute
            span.set_attribute(f"score.{attribute}", scores[attribute])
            span.set_attribute(f"weight.{attribute}", weights[attribute])
            span.set_attribute(f"contribution.{attribute}", round(contribution, 2))

        trust_score = round(trust_score, 2)
        span.set_attribute("trust_score.result", trust_score)

        return trust_score


def get_risk_flags(scores):
    with tracer.start_as_current_span("get_risk_flags") as span:
        flags = []

        if scores["fairness"] < 70:
            flags.append("Fairness below threshold")

        if scores["security"] < 80:
            flags.append("Security below threshold")

        if scores["compliance"] < 90:
            flags.append("Compliance below threshold")

        span.set_attribute("risk_flags.count", len(flags))
        span.set_attribute("risk_flags.values", flags)

        return flags


def generate_hash(data):
    with tracer.start_as_current_span("generate_evidence_hash") as span:
        json_data = json.dumps(data, sort_keys=True)
        span.set_attribute("hash.algorithm", "sha256")
        span.set_attribute("hash.input_size_bytes", len(json_data.encode()))

        digest = hashlib.sha256(json_data.encode()).hexdigest()
        span.set_attribute("hash.value", digest)

        return digest


# ---------------------------------------------------------------------------
# Main Logic — wrapped in a parent span so all 5 spans belong to one trace
# ---------------------------------------------------------------------------
with tracer.start_as_current_span("trust_score_pipeline") as parent_span:
    parent_span.set_attribute("pipeline.entity_count", len(scores))

    validate_input(scores, weights)

    trust_score = calculate_trust_score(scores, weights)

    risk_flags = get_risk_flags(scores)

    evidence = {
        "scores": scores,
        "weights": weights,
        "trust_score": trust_score,
        "risk_flags": risk_flags
    }

    hash_value = generate_hash(evidence)

    parent_span.set_attribute("pipeline.final_trust_score", trust_score)
    parent_span.set_attribute("pipeline.risk_flag_count", len(risk_flags))

    print("EVIDENCE ")
    print(json.dumps(evidence, indent=4))

    print("SHA-256 HASH")
    print(hash_value)

# Flush spans before the script exits so nothing gets dropped
provider.force_flush()