"""Pydantic v2 schemas for API validation and response serialization.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ProfilePredictRequest(BaseModel):
    """Input features required for single profile inference.
    
    Field aliases map internal models column names with spaces and special characters.
    """
    model_config = ConfigDict(populate_by_name=True)

    profile_pic: int = Field(
        ...,
        alias="profile pic",
        description="Profile picture present flag: 1 for yes, 0 for no",
        ge=0,
        le=1
    )
    nums_length_username: float = Field(
        ...,
        alias="nums/length username",
        description="Ratio of digits to username character length",
        ge=0.0,
        le=1.0
    )
    fullname_words: int = Field(
        ...,
        alias="fullname words",
        description="Word count in user's full name",
        ge=0,
        le=50
    )
    nums_length_fullname: float = Field(
        ...,
        alias="nums/length fullname",
        description="Ratio of digits to full name character length",
        ge=0.0,
        le=1.0
    )
    name_equals_username: int = Field(
        ...,
        alias="name==username",
        description="Flag indicating if full name equals username: 1 for yes, 0 for no",
        ge=0,
        le=1
    )
    description_length: int = Field(
        ...,
        alias="description length",
        description="Length of biography in characters",
        ge=0,
        le=2000
    )
    external_url: int = Field(
        ...,
        alias="external URL",
        description="External URL present flag: 1 for yes, 0 for no",
        ge=0,
        le=1
    )
    private: int = Field(
        ...,
        alias="private",
        description="Account privacy flag: 1 for private, 0 for public",
        ge=0,
        le=1
    )
    posts: int = Field(
        ...,
        alias="#posts",
        description="Total lifetime posts count",
        ge=0
    )
    followers: int = Field(
        ...,
        alias="#followers",
        description="Total followers count",
        ge=0
    )
    follows: int = Field(
        ...,
        alias="#follows",
        description="Total following count",
        ge=0
    )

    def to_feature_dict(self) -> Dict[str, Any]:
        """Convert validated schema back to exact feature dictionary expected by model pipeline."""
        return {
            "profile pic": self.profile_pic,
            "nums/length username": self.nums_length_username,
            "fullname words": self.fullname_words,
            "nums/length fullname": self.nums_length_fullname,
            "name==username": self.name_equals_username,
            "description length": self.description_length,
            "external URL": self.external_url,
            "private": self.private,
            "#posts": self.posts,
            "#followers": self.followers,
            "#follows": self.follows
        }


class FeatureContribution(BaseModel):
    feature: str
    value: Optional[float] = None
    contribution: float
    direction: Optional[str] = "Toward Fake"
    type: Optional[str] = "local"


class PredictResponse(BaseModel):
    label: str
    is_fake: int
    fake_probability: float
    genuine_probability: float
    risk_level: str
    top_features: List[FeatureContribution]
    timestamp: str


class BatchSummary(BaseModel):
    total_accounts: int
    low_risk_count: int
    needs_review_count: int
    high_risk_count: int
    fake_count: int
    genuine_count: int


class BatchPredictResponse(BaseModel):
    summary: BatchSummary
    predictions: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: Optional[str] = None
    target_column: Optional[str] = None
    features_count: Optional[int] = None

class QuickFillParseRequest(BaseModel):
    raw_text: Optional[str] = None
    username_or_url: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    posts: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    profile_pic: Optional[int] = 1
    is_private: Optional[int] = 0


class QuickFillPredictRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    full_name: Optional[str] = ""
    bio: Optional[str] = ""
    posts: int = Field(default=0, ge=0)
    followers: int = Field(default=0, ge=0)
    following: int = Field(default=0, ge=0)
    profile_pic: int = Field(default=1, ge=0, le=1)
    is_private: int = Field(default=0, ge=0, le=1)


class QuickFillParseResponse(BaseModel):
    detected_username: Optional[str] = None
    full_name: Optional[str] = ""
    bio: Optional[str] = ""
    posts: Optional[int] = 0
    followers: Optional[int] = 0
    following: Optional[int] = 0
    profile_pic: int = 1
    is_private: int = 0
    derived_features: Dict[str, Any]
