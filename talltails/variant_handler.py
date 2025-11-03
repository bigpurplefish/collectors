"""
Variant handling for Talltails collector.

Handles Magento product variants and swatch rendering.
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Set, Any
from bs4 import BeautifulSoup


class VariantHandler:
    """Handles Magento product variants."""

    def __init__(self):
        """Initialize variant handler."""
        pass

    @staticmethod
    def _norm_tokens(text: str) -> Set[str]:
        """Normalize text to token set."""
        return set(re.findall(r"[a-z0-9]+", (text or "").lower()))

    def extract_swatch_renderer(self, html: str) -> Dict[str, Any]:
        """
        Parse Magento swatch renderer config + visible swatch labels.

        Returns:
            product_labels: {child_id: [labels...]}
            product_media: {child_id: [gallery_items...]}
            style_opt_to_children: {option_id: [child_ids...]}
            style_opt_label: {option_id: "Label"}
            style_labels_dom: ["Yeti", "Gorilla", ...]
        """
        out: Dict[str, Any] = {
            "product_labels": {},
            "product_media": {},
            "style_opt_to_children": {},
            "style_opt_label": {},
            "style_labels_dom": [],
        }

        # Visible labels from DOM
        soup = BeautifulSoup(html, "html.parser")
        dom_labels: List[str] = []
        for el in soup.select('div.swatch-attribute.style .swatch-option'):
            lab = (el.get("data-option-label") or el.get_text(" ", strip=True) or "").strip()
            if lab:
                dom_labels.append(lab)
        out["style_labels_dom"] = list(dict.fromkeys(dom_labels))

        # text/x-magento-init JSON
        for mm in re.finditer(
            r'<script[^>]*type="text/x-magento-init"[^>]*>(.*?)</script>',
            html,
            re.I | re.DOTALL,
        ):
            blob = (mm.group(1) or "").strip()
            try:
                root = json.loads(blob)
            except Exception:
                continue

            def _walk(node: Any):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k == "Magento_Swatches/js/swatch-renderer" and isinstance(v, dict):
                            json_cfg = v.get("jsonConfig") or {}
                            attributes = json_cfg.get("attributes") or {}
                            index = json_cfg.get("index") or {}
                            media_gallery = v.get("mediaGallery") or v.get("gallery") or {}
                            images_by_child = json_cfg.get("images") or {}

                            # Identify "style" attribute
                            style_attr_id = None
                            for aid, meta in attributes.items():
                                if (meta.get("code") or "").lower() == "style":
                                    style_attr_id = str(aid)
                                    break

                            # Build option label map
                            opt_label: Dict[str, Dict[str, str]] = {}
                            for aid, meta in attributes.items():
                                mp = {}
                                for opt in meta.get("options", []):
                                    mp[str(opt.get("id"))] = str(opt.get("label") or "")
                                opt_label[str(aid)] = mp

                            # child -> labels from index
                            prod_labels: Dict[str, List[str]] = {}
                            if isinstance(index, dict):
                                for child_id, combo in index.items():
                                    labs: List[str] = []
                                    if isinstance(combo, dict):
                                        for aid, oid in combo.items():
                                            lab = opt_label.get(str(aid), {}).get(str(oid))
                                            if lab:
                                                labs.append(lab)
                                    if labs:
                                        prod_labels[str(child_id)] = labs

                            # attributes[].options[].products add labels + style mapping
                            for aid, meta in attributes.items():
                                for opt in meta.get("options", []):
                                    oid = str(opt.get("id"))
                                    lab = str(opt.get("label") or "")
                                    for child in opt.get("products") or []:
                                        cid = str(child)
                                        prod_labels.setdefault(cid, [])
                                        if lab and lab not in prod_labels[cid]:
                                            prod_labels[cid].append(lab)
                                    if style_attr_id and str(aid) == style_attr_id:
                                        out["style_opt_to_children"].setdefault(oid, [])
                                        for child in opt.get("products") or []:
                                            cid = str(child)
                                            if cid not in out["style_opt_to_children"][oid]:
                                                out["style_opt_to_children"][oid].append(cid)
                                        out["style_opt_label"][oid] = lab

                            # media maps
                            if isinstance(media_gallery, dict):
                                for cid, items in media_gallery.items():
                                    if isinstance(items, list) and items:
                                        out["product_media"][str(cid)] = items
                            if isinstance(images_by_child, dict):
                                for cid, items in images_by_child.items():
                                    if isinstance(items, list) and items:
                                        out["product_media"].setdefault(str(cid), items)

                            # merge labels
                            for cid, labs in prod_labels.items():
                                out["product_labels"].setdefault(cid, [])
                                for lab in labs:
                                    if lab not in out["product_labels"][cid]:
                                        out["product_labels"][cid].append(lab)

                        _walk(v)
                elif isinstance(node, list):
                    for v in node:
                        _walk(v)

            _walk(root)

        return out

    def fuzzy_style_from_name(
        self,
        style_labels: List[str],
        reference_text: str,
        tokens: Set[str]
    ) -> Tuple[Optional[str], float]:
        """
        Choose the best visible style label by fuzzy overlap with product name.

        Returns:
            (best_label, best_score)
        """
        if not style_labels:
            return (None, -1.0)

        ref = (reference_text or "").lower()
        ref = ref.replace("×", "x")
        ref = re.sub(r"[^a-z0-9\s-]", " ", ref)
        ref = re.sub(r"\s+", " ", ref)
        tokset = set(re.findall(r"[a-z0-9]+", ref)) | set(tokens or [])

        best = (None, -1.0)
        for lab in style_labels:
            l = (lab or "").lower().strip()
            l = l.replace("blackbear", "black bear")
            l = re.sub(r"\bgrizzle\b", "grizzly", l)
            score = 0.0
            if l in ref:
                score = 100.0
            else:
                ltoks = set(re.findall(r"[a-z0-9]+", l))
                score = float(len(ltoks & tokset)) + (0.1 if any(t in ref for t in ltoks) else 0.0)
            if score > best[1]:
                best = (lab, score)
        return best

    def best_style_option(
        self,
        style_opt_label: Dict[str, str],
        chosen_label: Optional[str]
    ) -> Optional[str]:
        """Map chosen visible label → swatch optionId (case-insensitive)."""
        if not chosen_label or not style_opt_label:
            return None

        cl = chosen_label.lower().replace("blackbear", "black bear")
        cl = re.sub(r"\bgrizzle\b", "grizzly", cl)

        best_oid, best_score = None, -1
        for oid, lab in style_opt_label.items():
            lab_l = (lab or "").lower()
            if lab_l == cl:
                return oid
            sc = 0
            if lab_l in cl or cl in lab_l:
                sc = 80
            else:
                sc = len(self._norm_tokens(lab_l) & self._norm_tokens(cl))
            if sc > best_score:
                best_oid, best_score = oid, sc
        return best_oid

    def select_variant_child(
        self,
        product_labels: Dict[str, List[str]],
        chosen_label: Optional[str],
        tokens: Set[str]
    ) -> Optional[str]:
        """Choose child by exact label first, else by label-token overlap."""
        if not product_labels:
            return None

        if chosen_label:
            cl = chosen_label.lower()
            for cid, labs in product_labels.items():
                for l in labs or []:
                    if (l or "").lower() == cl:
                        return cid

        best_id, best_score = None, -1
        tok_norm = self._norm_tokens((chosen_label or "") + " " + " ".join(tokens or []))
        for cid, labs in product_labels.items():
            ltok = self._norm_tokens(" ".join(labs or []))
            sc = len(ltok & tok_norm)
            if sc > best_score:
                best_id, best_score = cid, sc
        return best_id
