import re
from typing import Dict, Iterable, List, Set, Tuple

from lisa.projects.capability import CapabilityEvidence, CapabilityMatch
from lisa.projects.capability_request import CapabilityDiscoveryRequest
from lisa.projects.capability_result import CapabilityDiscoveryResult
from lisa.projects.profile_executor import ProjectProfileExecutor
from lisa.projects.profile_request import ProjectProfileRequest
from lisa.projects.registry import ProjectRegistry


class CapabilityDiscoveryExecutor:
    """Deterministic lexical discovery over project-profile evidence.

    This stage finds candidate locations only. It does not judge compatibility,
    recommend copying code, or authorize target modifications.
    """

    STOP_WORDS: Set[str] = {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "do",
        "for", "from", "how", "i", "in", "is", "it", "me", "of", "on",
        "or", "our", "project", "projects", "the", "to", "we", "what",
        "where", "with", "would",
    }

    SYNONYMS: Dict[str, Set[str]] = {
        "inventory": {"inventory", "stock", "stock_control", "stockcontrol"},
        "stocktake": {"stocktake", "stock_take", "stock_count", "stockcount"},
        "einvoice": {"einvoice", "e_invoice", "myinvois", "my_invois"},
        "checkout": {"checkout", "sales", "sale", "transaction", "transactions"},
        "sync": {"sync", "synchronization", "synchronisation", "replication"},
        "supplier": {"supplier", "vendor", "vendors"},
        "reporting": {"report", "reports", "reporting", "analytics"},
    }

    TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

    def __init__(self, registry=None, profile_executor=None):
        self._registry = registry or ProjectRegistry()
        self._profiles = profile_executor or ProjectProfileExecutor(registry=self._registry)

    @classmethod
    def _tokens(cls, text: str) -> Set[str]:
        return {
            token for token in cls.TOKEN_PATTERN.findall(text.casefold())
            if len(token) > 1 and token not in cls.STOP_WORDS
        }

    @classmethod
    def _expansions(cls, token: str) -> Set[str]:
        for group in cls.SYNONYMS.values():
            if token in group:
                return group
        return {token}

    @classmethod
    def _contains_any(cls, text: str, terms: Iterable[str]) -> bool:
        haystack = cls._tokens(text)
        for term in terms:
            normalized = cls._tokens(term)
            if normalized and normalized.issubset(haystack):
                return True
        return False

    def execute(self, request: CapabilityDiscoveryRequest) -> CapabilityDiscoveryResult:
        if not isinstance(request, CapabilityDiscoveryRequest):
            return CapabilityDiscoveryResult(
                success=False, error="A valid CapabilityDiscoveryRequest is required."
            )
        if not isinstance(request.query, str) or not request.query.strip():
            return CapabilityDiscoveryResult(success=False, error="A non-empty capability query is required.")
        if not 1 <= request.max_results <= 100:
            return CapabilityDiscoveryResult(success=False, error="max_results must be between 1 and 100.")

        query_terms = self._tokens(request.query)
        if not query_terms:
            return CapabilityDiscoveryResult(success=False, error="Query contains no searchable terms.")

        manifests = self._registry.list_manifests()
        if request.project_ids:
            requested = set(request.project_ids)
            known = {item.project_id for item in manifests}
            missing = sorted(requested - known)
            if missing:
                return CapabilityDiscoveryResult(
                    success=False,
                    error=f"Projects are not registered: {', '.join(missing)}",
                )
            manifests = [item for item in manifests if item.project_id in requested]

        matches: List[CapabilityMatch] = []
        for manifest in manifests:
            profile_result = self._profiles.execute(
                ProjectProfileRequest(project_id=manifest.project_id)
            )
            if not profile_result.success:
                continue
            profile = profile_result.profile
            evidence_text = "\n".join(item.excerpt for item in profile.evidence)
            path_text = "\n".join(profile.top_level_directories + profile.source_files_sample)
            corpus = evidence_text + "\n" + path_text

            matched = tuple(sorted(
                term for term in query_terms
                if self._contains_any(corpus, self._expansions(term))
            ))
            if not matched:
                continue

            evidence_refs = []
            for item in profile.evidence:
                if any(
                    self._contains_any(item.excerpt, self._expansions(term))
                    for term in matched
                ):
                    evidence_refs.append(CapabilityEvidence(
                        relative_path=item.relative_path,
                        evidence_kind=item.evidence_kind,
                        sha256=item.sha256,
                    ))

            source_paths = tuple(
                path for path in profile.source_files_sample
                if any(
                    self._contains_any(path, self._expansions(term))
                    for term in matched
                )
            )
            matches.append(CapabilityMatch(
                project_id=manifest.project_id,
                project_name=manifest.name,
                score=len(matched) / len(query_terms),
                matched_terms=matched,
                evidence=tuple(evidence_refs),
                source_paths=source_paths,
            ))

        matches.sort(key=lambda item: (-item.score, item.project_name.casefold(), item.project_id))
        return CapabilityDiscoveryResult(
            success=True,
            matches=tuple(matches[:request.max_results]),
        )
