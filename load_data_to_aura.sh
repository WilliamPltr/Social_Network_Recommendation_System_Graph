#!/bin/bash
# Script pour charger les données dans Neo4j AuraDB
# Usage: ./load_data_to_aura.sh

set -e  # Arrêter en cas d'erreur

echo "=========================================="
echo "Chargement des données vers Neo4j AuraDB"
echo "=========================================="
echo ""

# Configuration AuraDB
export NEO4J_URI="neo4j+s://512b23f4.databases.neo4j.io"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="0B86Fy9CXTpQRHw04w3isiiRQ8ZbBjW73aEtT4GMn2U"

echo "✓ Variables d'environnement configurées"
echo "  URI: $NEO4J_URI"
echo "  User: $NEO4J_USER"
echo ""

# Test de connexion
echo "Test de connexion à AuraDB..."
python -m scripts.test_connection
if [ $? -ne 0 ]; then
    echo "✗ Erreur de connexion. Vérifie tes identifiants."
    exit 1
fi
echo ""

# Charger les données SNAP
echo "=========================================="
echo "1/3 - Chargement des données SNAP..."
echo "=========================================="
python -m scripts.load_snap
if [ $? -ne 0 ]; then
    echo "✗ Erreur lors du chargement SNAP"
    exit 1
fi
echo ""

# Charger les jobs LinkedIn
echo "=========================================="
echo "2/3 - Chargement des jobs LinkedIn..."
echo "=========================================="
python -m scripts.load_jobs
if [ $? -ne 0 ]; then
    echo "✗ Erreur lors du chargement des jobs"
    exit 1
fi
echo ""

# Créer les embeddings utilisateurs
echo "=========================================="
echo "3/3 - Création des embeddings utilisateurs..."
echo "=========================================="
python -m scripts.create_user_embeddings
if [ $? -ne 0 ]; then
    echo "✗ Erreur lors de la création des embeddings"
    exit 1
fi
echo ""

# Vérification finale
echo "=========================================="
echo "Vérification finale..."
echo "=========================================="
python -m scripts.test_connection

echo ""
echo "=========================================="
echo "✓ Chargement terminé avec succès !"
echo "=========================================="
echo ""
echo "Tu peux maintenant tester sur Render :"
echo "  https://social-graph-api.onrender.com/api/debug/stats"
echo "  https://social-graph-api.onrender.com/"
echo ""


