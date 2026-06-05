"""Authentication endpoints: sign up and sign in via Supabase Auth."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.supabase_client import get_client

router = APIRouter(prefix="/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: str
    password: str
    full_name: str


class SignInRequest(BaseModel):
    email: str
    password: str


class SignUpResponse(BaseModel):
    message: str
    user_id: str


class SignInResponse(BaseModel):
    access_token: str
    user_id: str


@router.post("/signup", response_model=SignUpResponse)
async def signup(body: SignUpRequest) -> SignUpResponse:
    client = get_client()

    try:
        response = client.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {"data": {"full_name": body.full_name}},
            }
        )

        if response.user is None:
            raise ValueError("Sign up did not return a user")

        return SignUpResponse(
            message="Check your email to confirm your account",
            user_id=str(response.user.id),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)}) from e


@router.post("/signin", response_model=SignInResponse)
async def signin(body: SignInRequest) -> SignInResponse:
    client = get_client()

    try:
        response = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )

        if response.session is None or response.user is None:
            raise ValueError("Sign in did not return a session")

        return SignInResponse(
            access_token=response.session.access_token,
            user_id=str(response.user.id),
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid credentials"},
        )
