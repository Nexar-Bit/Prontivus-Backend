"""
TISS Denial Interpreter
Interprets and categorizes claim denials from operators
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DenialInterpreter:
    """Interpreter for TISS claim denials"""
    
    # Common denial codes mapping (simplified - should be expanded with full TISS codes)
    DENIAL_CODES = {
        # Technical denials
        '001': {'category': 'technical', 'description': 'Invalid XML format', 'action': 'fix_xml'},
        '002': {'category': 'technical', 'description': 'XSD validation error', 'action': 'fix_xml'},
        '003': {'category': 'technical', 'description': 'Missing required field', 'action': 'fix_data'},
        '004': {'category': 'technical', 'description': 'Invalid date format', 'action': 'fix_data'},
        
        # Business denials
        '101': {'category': 'business', 'description': 'Procedure not covered', 'action': 'review_coverage'},
        '102': {'category': 'business', 'description': 'Authorization required', 'action': 'request_authorization'},
        '103': {'category': 'business', 'description': 'Expired authorization', 'action': 'request_new_authorization'},
        '104': {'category': 'business', 'description': 'Patient not covered', 'action': 'verify_coverage'},
        '105': {'category': 'business', 'description': 'Procedure code mismatch', 'action': 'verify_code'},
        '106': {'category': 'business', 'description': 'ICD code mismatch', 'action': 'verify_diagnosis'},
        
        # Value denials
        '201': {'category': 'value', 'description': 'Value above limit', 'action': 'adjust_value'},
        '202': {'category': 'value', 'description': 'Value below minimum', 'action': 'adjust_value'},
        '203': {'category': 'value', 'description': 'Incorrect calculation', 'action': 'recalculate'},
        
        # Documentation denials
        '301': {'category': 'documentation', 'description': 'Missing documentation', 'action': 'provide_documentation'},
        '302': {'category': 'documentation', 'description': 'Invalid documentation', 'action': 'fix_documentation'},
        '303': {'category': 'documentation', 'description': 'Expired documentation', 'action': 'update_documentation'},
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def interpret_denial(self, denial_code: str, denial_message: Optional[str] = None) -> Dict:
        """
        Interpret a denial code and provide actionable information
        
        Args:
            denial_code: Denial code from operator
            denial_message: Optional denial message
            
        Returns:
            Dictionary with interpreted denial information
        """
        code_info = self.DENIAL_CODES.get(denial_code)
        
        if code_info:
            interpretation = {
                'code': denial_code,
                'category': code_info['category'],
                'description': code_info['description'],
                'action': code_info['action'],
                'message': denial_message or code_info['description'],
                'is_technical': code_info['category'] == 'technical',
                'is_business': code_info['category'] == 'business',
                'can_retry': code_info['category'] == 'technical',
                'requires_action': code_info['category'] != 'technical'
            }
        else:
            # Unknown code - try to infer from message
            interpretation = {
                'code': denial_code,
                'category': 'unknown',
                'description': denial_message or 'Unknown denial code',
                'action': 'contact_support',
                'message': denial_message or f'Unknown denial code: {denial_code}',
                'is_technical': False,
                'is_business': False,
                'can_retry': False,
                'requires_action': True
            }
            
            # Try to infer category from message
            if denial_message:
                message_lower = denial_message.lower()
                if any(word in message_lower for word in ['xml', 'xsd', 'format', 'schema', 'validation']):
                    interpretation['category'] = 'technical'
                    interpretation['is_technical'] = True
                    interpretation['can_retry'] = True
                elif any(word in message_lower for word in ['coverage', 'authorization', 'covered', 'plan']):
                    interpretation['category'] = 'business'
                    interpretation['is_business'] = True
        
        logger.info(f"Interpreted denial {denial_code} as {interpretation['category']}")
        return interpretation
    
    async def interpret_multiple_denials(self, denials: List[Dict]) -> Dict:
        """
        Interpret multiple denials and provide summary
        
        Args:
            denials: List of denial dictionaries with 'code' and optional 'message'
            
        Returns:
            Dictionary with interpreted denials and summary
        """
        interpreted = []
        categories = {}
        actions_needed = set()
        
        for denial in denials:
            code = denial.get('code')
            message = denial.get('message')
            
            interpretation = await self.interpret_denial(code, message)
            interpreted.append(interpretation)
            
            # Count by category
            category = interpretation['category']
            categories[category] = categories.get(category, 0) + 1
            
            # Collect actions needed
            if interpretation['action']:
                actions_needed.add(interpretation['action'])
        
        summary = {
            'total_denials': len(denials),
            'categories': categories,
            'actions_needed': list(actions_needed),
            'has_technical': any(d['is_technical'] for d in interpreted),
            'has_business': any(d['is_business'] for d in interpreted),
            'can_retry_all': all(d['can_retry'] for d in interpreted),
            'requires_action': any(d['requires_action'] for d in interpreted)
        }
        
        return {
            'denials': interpreted,
            'summary': summary
        }
    
    async def get_resolution_suggestions(self, denial_code: str) -> List[str]:
        """Get suggested resolution steps for a denial code"""
        code_info = self.DENIAL_CODES.get(denial_code)
        
        if not code_info:
            return ["Contact operator support for assistance with this denial code"]
        
        suggestions = {
            'fix_xml': [
                "Review XML structure",
                "Validate against XSD schema",
                "Check for missing or invalid elements",
                "Verify encoding is UTF-8"
            ],
            'fix_data': [
                "Review data fields",
                "Check for missing required fields",
                "Verify data formats (dates, numbers, etc.)",
                "Ensure data matches operator requirements"
            ],
            'review_coverage': [
                "Verify procedure is covered by patient's plan",
                "Check plan coverage table",
                "Contact operator to confirm coverage"
            ],
            'request_authorization': [
                "Request pre-authorization from operator",
                "Provide required documentation",
                "Wait for authorization before resubmitting"
            ],
            'request_new_authorization': [
                "Request new authorization (current one expired)",
                "Update authorization number in guide",
                "Resubmit with new authorization"
            ],
            'verify_coverage': [
                "Verify patient is active in plan",
                "Check coverage period",
                "Confirm patient data is correct"
            ],
            'verify_code': [
                "Verify procedure code matches TUSS table",
                "Check code is valid for date of service",
                "Ensure code matches service provided"
            ],
            'verify_diagnosis': [
                "Verify ICD-10 code is correct",
                "Check diagnosis matches procedure",
                "Ensure ICD code is valid and active"
            ],
            'adjust_value': [
                "Review value limits for procedure",
                "Adjust value to acceptable range",
                "Verify calculation is correct"
            ],
            'recalculate': [
                "Review calculation method",
                "Verify all components are included",
                "Recalculate according to operator rules"
            ],
            'provide_documentation': [
                "Gather required documentation",
                "Ensure documents are legible and complete",
                "Attach documentation to guide"
            ],
            'fix_documentation': [
                "Review documentation requirements",
                "Ensure documents meet operator standards",
                "Replace invalid documentation"
            ],
            'update_documentation': [
                "Obtain updated documentation",
                "Ensure documents are not expired",
                "Replace expired documentation"
            ]
        }
        
        return suggestions.get(code_info['action'], ["Review denial details and contact support if needed"])
    
    async def categorize_denials_by_severity(self, denials: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize denials by severity level"""
        categorized = {
            'critical': [],  # Cannot proceed, must fix
            'high': [],      # Significant impact, should fix
            'medium': [],    # Moderate impact, consider fixing
            'low': []        # Minor impact, optional fix
        }
        
        for denial in denials:
            category = denial.get('category', 'unknown')
            
            if category == 'technical':
                categorized['critical'].append(denial)
            elif category == 'business' and denial.get('action') in ['request_authorization', 'verify_coverage']:
                categorized['high'].append(denial)
            elif category == 'business':
                categorized['medium'].append(denial)
            elif category == 'value':
                categorized['medium'].append(denial)
            elif category == 'documentation':
                categorized['low'].append(denial)
            else:
                categorized['medium'].append(denial)
        
        return categorized

