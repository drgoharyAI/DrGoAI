"""
API Endpoints for Claim Category Management
Provides CRUD operations for managing claim categories
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from loguru import logger

from app.services.claim_classifier import claim_classifier, ClaimCategory
from app.services.fhir_parser import fhir_parser

router = APIRouter()


class CategoryCreate(BaseModel):
    """Schema for creating a new category"""
    category_id: str
    name: str
    description: str
    keywords: List[str] = []
    icd10_patterns: List[str] = []
    service_codes: List[str] = []
    priority: int = 5
    rules_file: Optional[str] = None
    rag_filter: Optional[Dict[str, Any]] = None
    enabled: bool = True


class CategoryUpdate(BaseModel):
    """Schema for updating a category"""
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    icd10_patterns: Optional[List[str]] = None
    service_codes: Optional[List[str]] = None
    priority: Optional[int] = None
    rules_file: Optional[str] = None
    rag_filter: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


@router.get(
    "",
    summary="List all claim categories",
    description="Get all configured claim categories with optional filtering"
)
async def list_categories(enabled_only: bool = True):
    """
    List all claim categories
    
    Args:
        enabled_only: If True, only return enabled categories
        
    Returns:
        List of categories with metadata
    """
    try:
        categories = claim_classifier.list_categories(enabled_only)
        return {
            "categories": categories,
            "total": len(categories),
            "enabled_count": len([c for c in categories if c.get('enabled', True)])
        }
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{category_id}",
    summary="Get specific category",
    description="Get details of a specific category by ID"
)
async def get_category(category_id: str):
    """
    Get details of a specific category
    
    Args:
        category_id: The category identifier
        
    Returns:
        Category details
    """
    category = claim_classifier.get_category(category_id)
    
    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category_id}' not found"
        )
    
    return category.to_dict()


@router.post(
    "",
    summary="Create new category",
    description="Create a new claim category with specified configuration"
)
async def create_category(category_data: CategoryCreate):
    """
    Create a new claim category
    
    Args:
        category_data: Category configuration
        
    Returns:
        Created category details
    """
    # Check if category already exists
    if claim_classifier.get_category(category_data.category_id):
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_data.category_id}' already exists"
        )
    
    # Create category
    try:
        category = ClaimCategory(
            category_id=category_data.category_id,
            name=category_data.name,
            description=category_data.description,
            keywords=category_data.keywords,
            icd10_patterns=category_data.icd10_patterns,
            service_codes=category_data.service_codes,
            priority=category_data.priority,
            rules_file=category_data.rules_file,
            rag_filter=category_data.rag_filter,
            enabled=category_data.enabled
        )
        
        success = claim_classifier.add_category(category)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create category"
            )
        
        logger.info(f"Created category: {category_data.category_id}")
        
        return {
            "message": "Category created successfully",
            "category": category.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{category_id}",
    summary="Update category",
    description="Update an existing category's configuration"
)
async def update_category(category_id: str, updates: CategoryUpdate):
    """
    Update an existing category
    
    Args:
        category_id: The category identifier
        updates: Fields to update
        
    Returns:
        Updated category details
    """
    # Convert to dict, removing None values
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(
            status_code=400,
            detail="No updates provided"
        )
    
    success = claim_classifier.update_category(category_id, update_dict)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category_id}' not found or update failed"
        )
    
    logger.info(f"Updated category: {category_id}")
    
    return {
        "message": "Category updated successfully",
        "category": claim_classifier.get_category(category_id).to_dict()
    }


@router.delete(
    "/{category_id}",
    summary="Delete category",
    description="Delete a category from the system"
)
async def delete_category(category_id: str):
    """
    Delete a category
    
    Args:
        category_id: The category identifier
        
    Returns:
        Success message
    """
    success = claim_classifier.delete_category(category_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category_id}' not found"
        )
    
    logger.info(f"Deleted category: {category_id}")
    
    return {
        "message": f"Category '{category_id}' deleted successfully"
    }


@router.get(
    "/stats/classification",
    summary="Get classification statistics",
    description="Get statistics on claim classifications performed"
)
async def get_classification_stats():
    """
    Get classification statistics
    
    Returns:
        Statistics on classifications
    """
    try:
        stats = claim_classifier.get_classification_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/test-classify",
    summary="Test claim classification",
    description="Test classification on a FHIR bundle without full adjudication"
)
async def test_classify(
    bundle_data: Dict[str, Any],
    use_llm: bool = True,
    confidence_threshold: float = 0.6
):
    """
    Test claim classification
    
    Useful for testing and validation without running full adjudication
    
    Args:
        bundle_data: FHIR bundle data
        use_llm: Whether to use LLM for classification
        confidence_threshold: Minimum confidence for category inclusion
        
    Returns:
        Classification results
    """
    try:
        # Parse FHIR bundle
        clinical_data = fhir_parser.parse_bundle(bundle_data)
        
        # Classify
        classification = claim_classifier.classify_claim(
            clinical_data=clinical_data,
            use_llm=use_llm,
            confidence_threshold=confidence_threshold
        )
        
        return classification
        
    except Exception as e:
        logger.error(f"Error in test classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
