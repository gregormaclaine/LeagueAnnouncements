from .certificate import Certificate
from riot import UserInfo, Rank


def generate_certificate(path: str, user: UserInfo, rank: Rank):
    cert = Certificate(user, rank)
    cert.build_image()
    cert.save(path)
