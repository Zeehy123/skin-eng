"""Score how well a product fits what the user told us."""  # module docstring: explain that product suitability is scored numerically

from __future__ import annotations  # allow postponed evaluation of type hints used in dataclass fields

from dataclasses import dataclass, field  # import dataclass utilities for score records and defaults

from .cautions import Restrictions  # import the restriction rules that may penalize ingredients
from .conditions import Context, condition_ok  # import user context and condition evaluator for rule checks
from .snapshot import Snapshot  # import the product and concern dataset used for scoring


@dataclass(frozen=True)  # the scoring numbers are configuration values; freezing prevents accidental mutation
class ScoringConfig:  # configuration for how strongly different factors affect a product's score
    """The numbers behind the scores. They come from the seed, so they can be tuned as data."""  # docstring says the score weights live in the snapshot data and can change easily

    band_multiplier: dict[str, float] = field(default_factory=dict)  # concern severity band -> multiplier for boosting matching ingredients
    position_cutoff: int = 5  # ingredient positions before this number are treated as early and higher-value
    late_position_factor: float = 0.5  # late-position ingredients get reduced weight
    care_penalty: float = 1.0  # penalty applied for ingredients that are allowed only with care

    @classmethod  # factory method to build this config from the snapshot's scoring section
    def from_snapshot(cls, snapshot: Snapshot) -> ScoringConfig:  # read the seed file's scoring settings
        data = snapshot.scoring  # the scoring rules from the snapshot
        return cls(  # create the config object from the snapshot values or sensible defaults
            band_multiplier=dict(data.get("band_multiplier", {})),  # convert the mapping to a normal dict
            position_cutoff=data.get("position_cutoff", 5),  # default cutoff if no config exists
            late_position_factor=data.get("late_position_factor", 0.5),  # default reduction for later ingredients
            care_penalty=data.get("care_penalty", 1.0),  # default penalty for care-only ingredients
        )


@dataclass  # a single ingredient match that boosts the product
class Match:  # one concern-driven ingredient match
    """One helpful ingredient found in a product."""  # docstring describes the meaning of a match

    concern: str  # the concern this ingredient is helping with
    ingredient: str  # ingredient code that matches the concern
    points: float  # numeric score contribution from this ingredient
    reason: str  # human-readable justification


@dataclass  # final score result for a product
class ProductScore:  # stores the total, each ingredient match, and penalty ingredients
    total: float  # total suitability score for this product
    matches: list[Match] = field(default_factory=list)  # all helpful matches that boosted the score
    penalties: list[str] = field(default_factory=list)  # ingredients that cost points because they require caution


def score_product(  # compute a product's suitability score for the current user
    snapshot: Snapshot,  # product and concern data source
    product: dict,  # the product being evaluated
    ctx: Context,  # user's context, including concern bands and flags
    restrictions: Restrictions,  # user-specific restriction rules
    config: ScoringConfig,  # scoring multipliers and thresholds
) -> ProductScore:  # returns the scored result for the product
    """points = (priority + boosts) x position factor x band multiplier, summed over matches."""  # docstring defines the formula for score calculation
    position_of = {code: index for index, code in enumerate(product["ingredients"])}  # map each ingredient to its index in the product formula

    matches = []  # collection of ingredient matches that add positive points
    for rule in snapshot.concern_ingredients:  # inspect every concern-based ingredient rule
        if rule["effect"] != "seek" or rule["concern"] not in ctx.concerns:  # only consider 'seek' rules for active concerns
            continue  # skip irrelevant rules
        position = position_of.get(rule["ingredient"])  # find this ingredient's position in the product
        if position is None or not condition_ok(rule["condition"], ctx):  # ignore ingredients absent from the product or rules that don't apply
            continue  # skip this rule because it does not match the current user/product pair

        boost = sum(b["boost"] for b in rule.get("boosts", []) if condition_ok(b["condition"], ctx))  # add extra points for condition-based boosts
        position_factor = 1.0 if position < config.position_cutoff else config.late_position_factor  # earlier ingredients are more valuable
        band = ctx.bands.get(rule["concern"])  # get the current severity band for the concern
        multiplier = config.band_multiplier.get(band, 1.0)  # multiply points based on how severe the concern is

        points = (rule["priority"] + boost) * position_factor * multiplier  # compute match points for this ingredient
        matches.append(Match(rule["concern"], rule["ingredient"], round(points, 4), rule["reason"]))  # store the match with rounded points and reason

    penalties = [code for code in product["ingredients"] if code in restrictions.care_ingredients]  # gather ingredients that are allowed only with care
    total = sum(m.points for m in matches) - config.care_penalty * len(penalties)  # subtract a penalty for each caution ingredient
    return ProductScore(round(total, 4), matches, penalties)  # return the final score object with rounded total and list of penalties
