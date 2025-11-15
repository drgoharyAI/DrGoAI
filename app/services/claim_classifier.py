"""
Claim Classifier Service
Classifies incoming pre-authorization requests into predefined categories
using LLM-powered analysis for intelligent routing to category-specific rules
"""
from typing import Dict, Any, List, Optional
from loguru import logger
import yaml
from pathlib import Path
from datetime import datetime
import json

from app.models.fhir_models import ParsedClinicalData
from app.services.llm_service import llm_service


class ClaimCategory:
    """Represents a claim category with its metadata"""
    def __init__(self, 
                 category_id: str, 
                 name: str, 
                 description: str,
                 keywords: List[str],
                 icd10_patterns: List[str],
                 service_codes: List[str],
                 priority: int = 0,
                 rules_file: Optional[str] = None,
                 rag_filter: Optional[Dict[str, Any]] = None,
                 enabled: bool = True):
        self.category_id = category_id
        self.name = name
        self.description = description
        self.keywords = keywords
        self.icd10_patterns = icd10_patterns
        self.service_codes = service_codes
        self.priority = priority  # Higher priority = checked first
        self.rules_file = rules_file
        self.rag_filter = rag_filter or {}
        self.enabled = enabled
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "icd10_patterns": self.icd10_patterns,
            "service_codes": self.service_codes,
            "priority": self.priority,
            "rules_file": self.rules_file,
            "rag_filter": self.rag_filter,
            "enabled": self.enabled
        }


class ClaimClassifier:
    """
    Intelligent claim classification system using LLM
    
    Workflow:
    1. Load predefined categories from YAML config
    2. Analyze clinical data + requested services
    3. Use LLM to classify into one or more categories
    4. Return categories with confidence scores
    5. Route to category-specific rules/RAG policies
    """
    
    def __init__(self, config_path: str = "app/config/claim_categories.yaml"):
        self.config_path = Path(config_path)
        self.categories: Dict[str, ClaimCategory] = {}
        self.classification_history: List[Dict[str, Any]] = []
        
        # Load categories
        self._load_categories()
        
        logger.info(f"✓ Claim Classifier initialized with {len(self.categories)} categories")
    
    def _load_categories(self):
        """Load claim categories from YAML configuration"""
        if not self.config_path.exists():
            logger.warning(f"Categories config not found: {self.config_path}")
            self._create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            for cat_data in config.get('categories', []):
                category = ClaimCategory(
                    category_id=cat_data['category_id'],
                    name=cat_data['name'],
                    description=cat_data['description'],
                    keywords=cat_data.get('keywords', []),
                    icd10_patterns=cat_data.get('icd10_patterns', []),
                    service_codes=cat_data.get('service_codes', []),
                    priority=cat_data.get('priority', 0),
                    rules_file=cat_data.get('rules_file'),
                    rag_filter=cat_data.get('rag_filter', {}),
                    enabled=cat_data.get('enabled', True)
                )
                
                if category.enabled:
                    self.categories[category.category_id] = category
            
            logger.info(f"✓ Loaded {len(self.categories)} claim categories")
            
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default KSA-specific categories configuration"""
        default_config = {
            'version': '1.0',
            'last_updated': datetime.utcnow().isoformat(),
            'categories': [
                {
                    'category_id': 'chronic_disease',
                    'name': 'Chronic Disease Management',
                    'description': 'Ongoing management of chronic conditions (diabetes, hypertension, asthma, etc.)',
                    'keywords': ['diabetes', 'hypertension', 'asthma', 'chronic', 'long-term', 'management'],
                    'icd10_patterns': ['E11', 'E10', 'I10', 'I11', 'J45', 'N18', 'I50'],
                    'service_codes': ['consultation', 'monitoring', 'medication_management'],
                    'priority': 8,
                    'rules_file': 'chronic_disease_rules.yaml',
                    'rag_filter': {'category': 'chronic_disease', 'type': 'management_protocol'}
                },
                {
                    'category_id': 'emergency',
                    'name': 'Emergency Services',
                    'description': 'Life-threatening conditions requiring immediate attention',
                    'keywords': ['emergency', 'urgent', 'life-threatening', 'trauma', 'acute', 'critical'],
                    'icd10_patterns': ['S', 'T', 'I21', 'I63', 'J96', 'R57'],
                    'service_codes': ['emergency_room', 'trauma', 'resuscitation'],
                    'priority': 10,
                    'rules_file': 'emergency_rules.yaml',
                    'rag_filter': {'category': 'emergency', 'auto_approve': True}
                },
                {
                    'category_id': 'surgical',
                    'name': 'Surgical Procedures',
                    'description': 'Elective and non-elective surgical interventions',
                    'keywords': ['surgery', 'operation', 'surgical', 'procedure', 'intervention'],
                    'icd10_patterns': ['Z', 'M'],
                    'service_codes': ['surgery', 'general_surgery', 'orthopedic_surgery', 'cardiac_surgery'],
                    'priority': 9,
                    'rules_file': 'surgical_rules.yaml',
                    'rag_filter': {'category': 'surgical', 'requires_preauth': True}
                },
                {
                    'category_id': 'diagnostic_imaging',
                    'name': 'Diagnostic Imaging',
                    'description': 'MRI, CT, X-ray, ultrasound, and other imaging services',
                    'keywords': ['mri', 'ct scan', 'x-ray', 'ultrasound', 'imaging', 'radiology'],
                    'icd10_patterns': ['R', 'M', 'S'],
                    'service_codes': ['mri', 'ct_scan', 'xray', 'ultrasound', 'pet_scan'],
                    'priority': 7,
                    'rules_file': 'imaging_rules.yaml',
                    'rag_filter': {'category': 'diagnostic', 'subcategory': 'imaging'}
                },
                {
                    'category_id': 'maternity',
                    'name': 'Maternity & Childbirth',
                    'description': 'Pregnancy, delivery, and postpartum care',
                    'keywords': ['pregnancy', 'maternity', 'delivery', 'childbirth', 'prenatal', 'postnatal'],
                    'icd10_patterns': ['O', 'Z3'],
                    'service_codes': ['prenatal_care', 'delivery', 'postnatal_care', 'c_section'],
                    'priority': 9,
                    'rules_file': 'maternity_rules.yaml',
                    'rag_filter': {'category': 'maternity', 'type': 'coverage'}
                },
                {
                    'category_id': 'oncology',
                    'name': 'Cancer Treatment',
                    'description': 'Cancer diagnosis, treatment, and management',
                    'keywords': ['cancer', 'oncology', 'chemotherapy', 'radiation', 'tumor', 'malignant'],
                    'icd10_patterns': ['C'],
                    'service_codes': ['chemotherapy', 'radiation_therapy', 'oncology_consultation'],
                    'priority': 10,
                    'rules_file': 'oncology_rules.yaml',
                    'rag_filter': {'category': 'oncology', 'high_priority': True}
                },
                {
                    'category_id': 'mental_health',
                    'name': 'Mental Health Services',
                    'description': 'Psychiatric and psychological services',
                    'keywords': ['mental', 'psychiatric', 'psychology', 'depression', 'anxiety', 'therapy'],
                    'icd10_patterns': ['F'],
                    'service_codes': ['psychiatry', 'psychology', 'counseling', 'therapy'],
                    'priority': 7,
                    'rules_file': 'mental_health_rules.yaml',
                    'rag_filter': {'category': 'mental_health', 'type': 'coverage'}
                },
                {
                    'category_id': 'dental',
                    'name': 'Dental Services',
                    'description': 'Dental care and treatments',
                    'keywords': ['dental', 'teeth', 'oral', 'dentistry', 'orthodontic'],
                    'icd10_patterns': ['K0'],
                    'service_codes': ['dental_consultation', 'dental_surgery', 'orthodontics'],
                    'priority': 5,
                    'rules_file': 'dental_rules.yaml',
                    'rag_filter': {'category': 'dental', 'type': 'coverage'}
                },
                {
                    'category_id': 'rehabilitation',
                    'name': 'Rehabilitation Services',
                    'description': 'Physical therapy, occupational therapy, speech therapy',
                    'keywords': ['rehabilitation', 'therapy', 'physical therapy', 'occupational', 'speech'],
                    'icd10_patterns': ['M', 'G', 'S'],
                    'service_codes': ['physical_therapy', 'occupational_therapy', 'speech_therapy'],
                    'priority': 6,
                    'rules_file': 'rehabilitation_rules.yaml',
                    'rag_filter': {'category': 'rehabilitation', 'type': 'protocol'}
                },
                {
                    'category_id': 'pharmacy',
                    'name': 'Medication & Pharmacy',
                    'description': 'Prescription medications and specialty drugs',
                    'keywords': ['medication', 'drug', 'prescription', 'pharmacy', 'specialty drug'],
                    'icd10_patterns': ['Z'],
                    'service_codes': ['medication', 'specialty_medication', 'biologic_agents'],
                    'priority': 6,
                    'rules_file': 'pharmacy_rules.yaml',
                    'rag_filter': {'category': 'pharmacy', 'type': 'formulary'}
                },
                {
                    'category_id': 'preventive',
                    'name': 'Preventive Care',
                    'description': 'Routine checkups, screenings, and vaccinations',
                    'keywords': ['preventive', 'screening', 'checkup', 'vaccination', 'immunization'],
                    'icd10_patterns': ['Z00', 'Z01', 'Z11', 'Z12'],
                    'service_codes': ['routine_checkup', 'screening', 'vaccination'],
                    'priority': 5,
                    'rules_file': 'preventive_rules.yaml',
                    'rag_filter': {'category': 'preventive', 'auto_approve': True}
                },
                {
                    'category_id': 'cardiology',
                    'name': 'Cardiac Care',
                    'description': 'Heart-related conditions and procedures',
                    'keywords': ['cardiac', 'heart', 'cardiology', 'cardiovascular', 'coronary'],
                    'icd10_patterns': ['I2', 'I3', 'I4', 'I5'],
                    'service_codes': ['cardiology_consultation', 'cardiac_catheterization', 'ecg', 'echo'],
                    'priority': 9,
                    'rules_file': 'cardiology_rules.yaml',
                    'rag_filter': {'category': 'cardiology', 'high_cost': True}
                },
                {
                    'category_id': 'nephrology',
                    'name': 'Kidney Care',
                    'description': 'Kidney disease and dialysis',
                    'keywords': ['kidney', 'renal', 'dialysis', 'nephrology'],
                    'icd10_patterns': ['N18', 'N19'],
                    'service_codes': ['dialysis', 'nephrology_consultation'],
                    'priority': 9,
                    'rules_file': 'nephrology_rules.yaml',
                    'rag_filter': {'category': 'nephrology', 'type': 'chronic_care'}
                },
                {
                    'category_id': 'cosmetic',
                    'name': 'Cosmetic Procedures',
                    'description': 'Non-medically necessary cosmetic procedures',
                    'keywords': ['cosmetic', 'aesthetic', 'beauty', 'elective'],
                    'icd10_patterns': [],
                    'service_codes': ['cosmetic_surgery', 'aesthetic_procedure'],
                    'priority': 3,
                    'rules_file': 'cosmetic_rules.yaml',
                    'rag_filter': {'category': 'cosmetic', 'auto_deny': True}
                },
                {
                    'category_id': 'high_cost',
                    'name': 'High-Cost Services',
                    'description': 'Services exceeding cost thresholds requiring special review',
                    'keywords': ['expensive', 'high cost', 'specialized'],
                    'icd10_patterns': [],
                    'service_codes': [],
                    'priority': 8,
                    'rules_file': 'high_cost_rules.yaml',
                    'rag_filter': {'category': 'high_cost', 'requires_senior_review': True}
                }
            ]
        }
        
        # Create directory if needed
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save default config
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"✓ Created default categories config at {self.config_path}")
        
        # Load the created config
        self._load_categories()
    
    def classify_claim(
        self,
        clinical_data: ParsedClinicalData,
        use_llm: bool = True,
        confidence_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Classify claim into one or more categories
        
        Args:
            clinical_data: Parsed clinical data from FHIR bundle
            use_llm: Whether to use LLM for classification (more accurate)
            confidence_threshold: Minimum confidence to include a category
            
        Returns:
            Dictionary with:
            - categories: List of matched categories with scores
            - primary_category: Highest confidence category
            - classification_method: 'llm' or 'rule_based'
            - timestamp: Classification timestamp
        """
        logger.info(f"Classifying claim {clinical_data.request_id}...")
        
        # Method 1: Rule-based classification (fast, always runs)
        rule_based_matches = self._rule_based_classification(clinical_data)
        
        # Method 2: LLM-based classification (more accurate, optional)
        if use_llm and llm_service.use_gemini:
            llm_matches = self._llm_classification(clinical_data)
            # Merge and average scores
            final_matches = self._merge_classifications(rule_based_matches, llm_matches)
            method = 'llm_enhanced'
        else:
            final_matches = rule_based_matches
            method = 'rule_based'
        
        # Filter by confidence threshold
        filtered_matches = {
            cat_id: score 
            for cat_id, score in final_matches.items() 
            if score >= confidence_threshold
        }
        
        # Sort by score (highest first)
        sorted_matches = sorted(
            filtered_matches.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Determine primary category
        primary_category = sorted_matches[0][0] if sorted_matches else 'general'
        
        # Build result
        result = {
            'request_id': clinical_data.request_id,
            'categories': [
                {
                    'category_id': cat_id,
                    'name': self.categories[cat_id].name,
                    'confidence': score,
                    'priority': self.categories[cat_id].priority,
                    'rules_file': self.categories[cat_id].rules_file,
                    'rag_filter': self.categories[cat_id].rag_filter
                }
                for cat_id, score in sorted_matches
            ],
            'primary_category': primary_category,
            'primary_category_name': self.categories[primary_category].name if primary_category in self.categories else 'General',
            'classification_method': method,
            'timestamp': datetime.utcnow().isoformat(),
            'total_categories_matched': len(sorted_matches)
        }
        
        # Log classification
        logger.info(f"✓ Classified as: {result['primary_category_name']} "
                   f"(+ {len(sorted_matches)-1} other categories)")
        
        # Store in history
        self.classification_history.append(result)
        
        return result
    
    def _rule_based_classification(
        self,
        clinical_data: ParsedClinicalData
    ) -> Dict[str, float]:
        """
        Rule-based classification using keywords, ICD-10, and service codes
        Returns dictionary of category_id -> confidence score (0-1)
        """
        scores = {}
        
        for cat_id, category in self.categories.items():
            score = 0.0
            matches = 0
            total_checks = 0
            
            # Check 1: Diagnosis codes (ICD-10 patterns)
            if category.icd10_patterns and clinical_data.diagnosis_codes:
                total_checks += 1
                for dx_code in clinical_data.diagnosis_codes:
                    for pattern in category.icd10_patterns:
                        if dx_code.startswith(pattern):
                            matches += 1
                            break
            
            # Check 2: Service codes
            if category.service_codes:
                total_checks += 1
                for service in clinical_data.services:
                    service_type = service.service_type.lower()
                    if any(code.lower() in service_type for code in category.service_codes):
                        matches += 1
                        break
            
            # Check 3: Keywords in clinical notes
            if category.keywords:
                total_checks += 1
                clinical_text = ' '.join([
                    service.clinical_notes or '' 
                    for service in clinical_data.services
                ]).lower()
                
                keyword_matches = sum(
                    1 for keyword in category.keywords 
                    if keyword.lower() in clinical_text
                )
                
                if keyword_matches > 0:
                    matches += min(keyword_matches, 3)  # Cap at 3 for keyword matches
            
            # Check 4: Cost-based classification (high_cost category)
            if cat_id == 'high_cost':
                total_checks += 1
                total_cost = sum(service.requested_amount or 0 for service in clinical_data.services)
                if total_cost > 50000:  # High cost threshold (SAR)
                    matches += 1
            
            # Calculate score
            if total_checks > 0:
                score = matches / (total_checks * 1.5)  # Normalized score
                score = min(score, 1.0)  # Cap at 1.0
            
            if score > 0:
                scores[cat_id] = score
        
        return scores
    
    def _llm_classification(
        self,
        clinical_data: ParsedClinicalData
    ) -> Dict[str, float]:
        """
        Use LLM to classify claim based on clinical understanding
        Returns dictionary of category_id -> confidence score (0-1)
        """
        try:
            # Prepare clinical summary for LLM
            summary = self._prepare_clinical_summary(clinical_data)
            
            # Prepare category descriptions for LLM
            category_list = '\n'.join([
                f"- {cat.category_id}: {cat.name} - {cat.description}"
                for cat in self.categories.values()
            ])
            
            # Create LLM prompt
            prompt = f"""You are a medical claims classifier for a Saudi health insurance company.

Analyze the following pre-authorization request and classify it into one or more of the predefined categories.

CLINICAL DATA:
{summary}

AVAILABLE CATEGORIES:
{category_list}

TASK:
1. Identify ALL relevant categories for this claim (a claim can belong to multiple categories)
2. For each category, provide a confidence score from 0.0 to 1.0
3. Consider the primary diagnosis, requested services, and clinical context

RESPOND ONLY with valid JSON in this exact format:
{{
    "classifications": [
        {{"category_id": "category_name", "confidence": 0.95, "reason": "brief explanation"}},
        {{"category_id": "another_category", "confidence": 0.75, "reason": "brief explanation"}}
    ],
    "primary_category": "most_relevant_category_id"
}}

DO NOT include any text outside the JSON object. The response must be valid, parseable JSON."""

            # Call Google Gemini
            if llm_service.use_gemini:
                response = llm_service.gemini_model.generate_content(prompt)
                response_text = response.text
            else:
                logger.warning("⚠️ Gemini not available for classification")
                return {}
            
            # Parse JSON response
            response_text = response_text.strip()
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            classification_result = json.loads(response_text)
            
            # Convert to scores dictionary
            scores = {}
            for item in classification_result.get('classifications', []):
                cat_id = item['category_id']
                confidence = float(item['confidence'])
                
                # Validate category exists
                if cat_id in self.categories:
                    scores[cat_id] = confidence
                    logger.debug(f"  LLM: {cat_id} = {confidence:.2f} ({item.get('reason', 'N/A')})")
            
            return scores
            
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            return {}
    
    def _merge_classifications(
        self,
        rule_based: Dict[str, float],
        llm_based: Dict[str, float],
        rule_weight: float = 0.4,
        llm_weight: float = 0.6
    ) -> Dict[str, float]:
        """
        Merge rule-based and LLM-based classifications
        LLM gets higher weight as it's more accurate
        """
        all_categories = set(rule_based.keys()) | set(llm_based.keys())
        merged = {}
        
        for cat_id in all_categories:
            rule_score = rule_based.get(cat_id, 0.0)
            llm_score = llm_based.get(cat_id, 0.0)
            
            # Weighted average
            merged_score = (rule_score * rule_weight) + (llm_score * llm_weight)
            merged[cat_id] = merged_score
        
        return merged
    
    def _prepare_clinical_summary(self, clinical_data: ParsedClinicalData) -> str:
        """Prepare concise clinical summary for LLM"""
        summary_parts = []
        
        # Patient info
        summary_parts.append(f"Patient: {clinical_data.patient_id}, Age: {clinical_data.patient_age or 'N/A'}")
        
        # Diagnoses
        if clinical_data.diagnosis_codes:
            summary_parts.append(f"Diagnoses: {', '.join(clinical_data.diagnosis_codes)}")
        
        # Services requested
        services_summary = []
        for service in clinical_data.services:
            service_desc = f"{service.service_type}"
            if service.requested_amount:
                service_desc += f" (SAR {service.requested_amount})"
            if service.clinical_notes:
                service_desc += f" - {service.clinical_notes[:100]}"
            services_summary.append(service_desc)
        
        summary_parts.append(f"Requested Services:\n  " + "\n  ".join(services_summary))
        
        return "\n".join(summary_parts)
    
    # === CRUD Operations for Categories ===
    
    def add_category(self, category: ClaimCategory) -> bool:
        """Add a new category"""
        try:
            self.categories[category.category_id] = category
            self._save_categories()
            logger.info(f"✓ Added category: {category.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            return False
    
    def update_category(self, category_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing category"""
        if category_id not in self.categories:
            logger.error(f"Category not found: {category_id}")
            return False
        
        try:
            category = self.categories[category_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            
            self._save_categories()
            logger.info(f"✓ Updated category: {category.name}")
            return True
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return False
    
    def delete_category(self, category_id: str) -> bool:
        """Delete a category"""
        if category_id not in self.categories:
            logger.error(f"Category not found: {category_id}")
            return False
        
        try:
            del self.categories[category_id]
            self._save_categories()
            logger.info(f"✓ Deleted category: {category_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False
    
    def get_category(self, category_id: str) -> Optional[ClaimCategory]:
        """Get a specific category"""
        return self.categories.get(category_id)
    
    def list_categories(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """List all categories"""
        categories = [
            cat.to_dict() 
            for cat in self.categories.values()
            if not enabled_only or cat.enabled
        ]
        return sorted(categories, key=lambda x: x['priority'], reverse=True)
    
    def _save_categories(self):
        """Save categories back to YAML file"""
        config = {
            'version': '1.0',
            'last_updated': datetime.utcnow().isoformat(),
            'categories': [cat.to_dict() for cat in self.categories.values()]
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.debug(f"✓ Saved {len(self.categories)} categories to config")
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics"""
        if not self.classification_history:
            return {'total_classifications': 0}
        
        # Calculate stats
        category_counts = {}
        method_counts = {'llm_enhanced': 0, 'rule_based': 0}
        
        for record in self.classification_history:
            # Count primary categories
            primary = record['primary_category']
            category_counts[primary] = category_counts.get(primary, 0) + 1
            
            # Count methods
            method = record['classification_method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            'total_classifications': len(self.classification_history),
            'category_distribution': category_counts,
            'method_distribution': method_counts,
            'average_categories_per_claim': sum(
                len(r['categories']) for r in self.classification_history
            ) / len(self.classification_history)
        }


# Global instance
claim_classifier = ClaimClassifier()
