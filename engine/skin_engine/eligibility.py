# Decide whether a product may be recommended at all, and say why not.  # module comment: this file checks if a product is allowed

from __future__ import annotations  
# allow type hints like str | None to be evaluated later

from .cautions import Restrictions  
# import the restriction data object used to check avoid/care rules
from .conditions import Context 
 # import the user context describing skin, flags, concerns, etc.
from .snapshot import Snapshot 
 # import the snapshot with product and ingredient metadata


def exclusion_reasons( 
    snapshot: Snapshot, product: dict, ctx: Context, restrictions: Restrictions  # snapshot, selected product, user context, calculated restrictions
# define the function that returns all reasons a product is blocked
) -> list[str]: 
     # return a list of human-readable blocking reasons
    """An empty list means the product is eligible. Otherwise every reason is listed."""  # docstring tells callers that an empty result means the product is allowed
    reasons = [] 
 # start with no reasons at all; each rejection adds a message here
    if not product.get("active", True):
# if the product is marked inactive or unavailable, it cannot be recommended
        reasons.append("Not currently available.")  
# add the message explaining why it is excluded
    if ctx.skin_type not in product["skin_types"]:  
# if the user's skin type is not supported by this product, reject it
        reasons.append(f"Not designed for {ctx.skin_type} skin.")  
# add the reason with the user's actual skin type
    for code in product["ingredients"]:  
# walk every ingredient listed in the product
        name = snapshot.ingredient_name(code) 
# look up the ingredient's friendly name so the message is readable
        for why in restrictions.avoid_ingredients.get(code, []):  
# check all reasons this ingredient is forbidden for this user
            reasons.append(f"Contains {name}. {why}")  
# add a message like: Contains niacinamide. Avoid because...
    for why in restrictions.avoid_forms.get(product["form"], []):  
# check the product form (cream, serum, etc.) for forbidden reasons
        reasons.append(f"It is a {product['form']} product. {why}")  
# add a message explaining that this form is restricted
    return list(dict.fromkeys(reasons))  
# remove repeats while keeping the original order of unique reasons
