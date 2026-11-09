"""Choose a routine template and fill each step with the best product."""  # module docstring: select a template and assign the best products to each routine step

from __future__ import annotations  # allow postponed evaluation of type hints for dataclasses and return types

from dataclasses import dataclass, field  # import dataclass and field helpers for routine-step records

from .analysis import Analysis  # import the analysis object containing user context and restriction data
from .conditions import Context, condition_ok  # import user context and condition evaluator for matching templates
from .explain import explain_pick  # import the helper that writes the product summary and reasons
from .scoring import ProductScore, ScoringConfig, score_product  # import product scoring utilities and the score function
from .snapshot import Snapshot  # import the data source for products, templates, and rules

MAX_ALTERNATIVES = 2  # keep at most two alternative products per step in the final result


@dataclass  # define a single product choice for a routine step
class Pick:  # a chosen product with summary and reasons
    code: str  # product code, used as the unique identifier
    name: str  # display name of the product
    form: str  # product form such as serum, cream, or cleanser
    price_kobo: int  # price in kobo for sorting cheaper items first
    score: float  # how suitable the product is according to scoring
    summary: str  # short explanation shown to the user
    reasons: list[str]  # detailed reasons why this product matches


@dataclass  # define a single step in the final skincare routine
class RoutineStep:  # one routine step (for example cleanser, serum, sunscreen)
    step: str  # the step name
    required: bool  # whether the step is mandatory
    priority: int  # importance or required priority value from the user's answers
    pick: Pick | None  # the selected product for this step, if any
    alternatives: list[Pick] = field(default_factory=list)  # alternative products the user could swap in
    note: str | None = None  # optional note if no product is available


def choose_template(snapshot: Snapshot, ctx: Context) -> dict:  # choose the best matching routine template for the user
    """The matching template with the highest priority (the first one wins a tie)."""  # docstring: picks the highest-priority matching template
    matching = [t for t in snapshot.templates if condition_ok(t["condition"], ctx)]  # keep only templates whose condition matches the user
    if not matching:  # if nothing matches, fail loudly; there should be a default template
        raise ValueError("No routine template matches; add a default template (empty condition).")  # raise an explicit error for missing defaults
    return max(matching, key=lambda template: template["priority"])  # highest priority wins; ties break by default max behavior


def build_routine(  # assemble the routine using the selected template and eligible products
    snapshot: Snapshot, analysis: Analysis, eligible: list[str], config: ScoringConfig  # snapshot, analysis result, eligible products, and scoring config
) -> tuple[dict, list[RoutineStep]]:  # return the template and list of routine steps
    template = choose_template(snapshot, analysis.ctx)  # pick the best template for this context
    specs = [dict(spec) for spec in template["steps"]]  # make a working copy of the template's steps

    present = {spec["step"] for spec in specs}  # remember which steps already exist in the template
    for step in sorted(analysis.tally.required_steps):  # add any additional required steps from the user's answers
        if step not in present:  # skip steps already covered by the template
            specs.append({"step": step, "required": True})  # add the missing required step with the same kind of requirement

    routine = [_fill_step(snapshot, analysis, spec, eligible, config) for spec in specs]  # fill every step with a product candidate
    return template, routine  # return both the template metadata and the completed routine steps


def _fill_step(  # fill one routine step with the top product and alternatives
    snapshot: Snapshot, analysis: Analysis, spec: dict, eligible: list[str], config: ScoringConfig  # product data and scoring config for this step
) -> RoutineStep:  # return the completed step
    ctx = analysis.ctx  # the user's current context is used to score each product
    step = spec["step"]  # step name to fill, such as cleanser or sunscreen
    priority = analysis.tally.required_steps.get(step, 0)  # get priority from the talled answers for this step
    required = spec.get("required", False) or priority > 0  # a step is required either by the template or by a user answer
    preferred = spec.get("preferred_forms", [])  # preferred forms for this step, if any

    scored = [  # score every eligible product that belongs to this step
        (product, score_product(snapshot, product, ctx, analysis.restrictions, config))  # product and its final score
        for product in (snapshot.products[code] for code in eligible)  # iterate eligible product records
        if product["step"] == step  # keep only products that belong to the current step
    ]
    scored.sort(key=lambda pair: _rank_key(pair[0], pair[1], preferred))  # sort best candidates first using ranking rules

    picks = [_make_pick(snapshot, product, score, ctx) for product, score in scored]  # convert scored products to Pick objects
    if not picks:  # if no product is suitable for this step, record the miss instead of crashing
        return RoutineStep(  # create a step with no product selected
            step, required, priority, None, note="No suitable product in this catalogue."  # step name, required status, priority, missing pick, and note
        )
    return RoutineStep(step, required, priority, picks[0], picks[1 : 1 + MAX_ALTERNATIVES])  # keep the top pick and up to two alternatives


def _rank_key(product: dict, score: ProductScore, preferred_forms: list[str]) -> tuple:  # define how to rank products within a step
    """Best first: higher score, then preferred form, then cheaper, then code (for stability)."""  # docstring explains sort priority
    form = product["form"]  # product form (cream, serum, etc.)
    form_rank = preferred_forms.index(form) if form in preferred_forms else len(preferred_forms)  # lower is better when a preferred form is listed
    return (-score.total, form_rank, product["price_kobo"], product["code"])  # ranking tuple: highest score first, then preferred form, then cheaper, then stable code


def _make_pick(snapshot: Snapshot, product: dict, score: ProductScore, ctx: Context) -> Pick:  # convert a scored product into a user-visible Pick
    summary, reasons = explain_pick(snapshot, score, ctx)  # generate the summary sentence and detailed reasons
    return Pick(  # store the final data used in the routine output
        code=product["code"],  # product code
        name=product["name"],  # user-friendly name
        form=product["form"],  # product form
        price_kobo=product["price_kobo"],  # price in kobo
        score=score.total,  # final numeric score
        summary=summary,  # summary explanation text
        reasons=reasons,  # list of detailed reasons for the pick
    )
