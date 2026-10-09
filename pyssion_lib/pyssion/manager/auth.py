"""Opaque bearer tokens, stored hashed. Kinds scope what a caller may do."""
import hashlib
import secrets
import time

from fastapi import Depends, Header, HTTPException

from .db import Token, get


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue(s, kind, subject="", uses=None, ttl=None):
    token = f"ps{kind[0]}_{secrets.token_urlsafe(24)}"
    s.add(Token(hash=digest(token), kind=kind, subject=subject, uses=uses, expires=time.time() + ttl if ttl else None))
    s.commit()
    return token


def lookup(s, token, kinds):
    t = s.get(Token, digest(token or ""))
    if not t or t.kind not in kinds or (t.expires and t.expires < time.time()) or t.uses == 0:
        raise HTTPException(401, "invalid token")
    return t


def revoke(s, kind, subject):
    s.query(Token).filter_by(kind=kind, subject=subject).delete()


def require(*kinds):
    def dep(authorization: str = Header(""), s=Depends(get)):
        return lookup(s, authorization.removeprefix("Bearer "), kinds)
    return Depends(dep)


ADMIN = require("admin")
USER = require("admin", "user")
NODE = require("node")
STORE = require("admin", "user", "job")
