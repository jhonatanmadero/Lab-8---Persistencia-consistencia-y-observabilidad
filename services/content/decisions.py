"""ÚNICO archivo de código que deben modificar los estudiantes.
La base arranca, pero los tres TODO incumplen contratos intencionalmente.
Consultar README y docs/CONTRATOS.md antes de cambiar cada función.
"""
from pymongo import ReturnDocument
from redis.exceptions import RedisError

def save_board(collection, board_id, expected_version, title):
    # Control optimista: la comparación de versión y el incremento ocurren en una sola
    # operación atómica de MongoDB. Una versión obsoleta no coincide -> None (409).
    return collection.find_one_and_update(
        {'_id': board_id, 'version': expected_version},
        {'$set': {'title': title}, '$inc': {'version': 1}},
        return_document=ReturnDocument.AFTER,
    )

def permission_for_write(user, board_id, cached_permission, authoritative_permission):
    # Una concesión en caché no prueba que siga vigente: las escrituras consultan siempre
    # la autoridad (Gestión/PostgreSQL). Su 503 se propaga a propósito para no escribir
    # con una concesión vieja. La caché queda solo para la lectura de la interfaz.
    return authoritative_permission(user, board_id)

def touch_presence(client, key, ttl):
    # Valor y expiración en un único SET (EX); cada heartbeat renueva el TTL.
    # Si Redis falla, solo se degrada la presencia: se informa False sin romper la petición.
    try:
        client.set(key, 'online', ex=ttl)
    except RedisError:
        return False
    return True
