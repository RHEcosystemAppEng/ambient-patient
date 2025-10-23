"""Custom actions for patient intake NemoGuard."""

from nemoguardrails.actions import action


@action()
def check_policy_for_keyword(policy_violations: list, keyword: str) -> bool:
    """
    Check if any policy violation contains the specified keyword as a substring.
    
    Args:
        policy_violations: List of policy violation strings
        keyword: Keyword to search for in each violation
        
    Returns:
        True if keyword is found in any violation, False otherwise
    """
    if not policy_violations:
        return False
    
    return any(keyword.lower() in str(violation).lower() for violation in policy_violations)

