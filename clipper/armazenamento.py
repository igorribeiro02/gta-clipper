"""Sobe o vídeo pronto num bucket Cloudflare R2 público (grátis até 10 GB)
para o Metricool conseguir buscar o arquivo por URL."""
import os

import boto3


def subir(caminho: str, nome: str) -> str:
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    bucket = os.environ["R2_BUCKET"]
    s3.upload_file(caminho, bucket, nome, ExtraArgs={"ContentType": "video/mp4"})
    return f"{os.environ['R2_PUBLIC_BASE_URL'].rstrip('/')}/{nome}"
