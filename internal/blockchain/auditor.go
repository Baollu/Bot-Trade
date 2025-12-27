package blockchain

import (
	"context"
	"crypto/ecdsa"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"os"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
)

// TradeRecord représente un enregistrement de trade pour la blockchain
type TradeRecord struct {
	Symbol     string    `json:"symbol"`
	Type       string    `json:"type"`
	Price      float64   `json:"price"`
	Quantity   float64   `json:"quantity"`
	Profit     float64   `json:"profit"`
	ExecutedAt time.Time `json:"executed_at"`
	Confidence float64   `json:"confidence"`
}

// BlockchainAuditor gère l'audit des trades sur Ethereum Sepolia
type BlockchainAuditor struct {
	client     *ethclient.Client
	privateKey *ecdsa.PrivateKey
	address    common.Address
	chainID    *big.Int
	ctx        context.Context
	enabled    bool
}

// NewBlockchainAuditor crée une nouvelle instance de l'auditeur blockchain
func NewBlockchainAuditor() (*BlockchainAuditor, error) {
	// Récupération des variables d'environnement
	rpcURL := os.Getenv("SEPOLIA_RPC_URL")
	privateKeyHex := os.Getenv("PRIVATE_KEY")

	// Si pas configuré, retourner un auditeur désactivé
	if rpcURL == "" || privateKeyHex == "" {
		log.Println("⚠️ Blockchain non configurée - Audit désactivé")
		log.Println("   Configurez SEPOLIA_RPC_URL et PRIVATE_KEY pour activer")
		return &BlockchainAuditor{enabled: false}, nil
	}

	// Connexion au réseau Sepolia
	client, err := ethclient.Dial(rpcURL)
	if err != nil {
		return nil, fmt.Errorf("erreur connexion Sepolia: %w", err)
	}

	// Chargement de la clé privée
	privateKey, err := crypto.HexToECDSA(privateKeyHex)
	if err != nil {
		return nil, fmt.Errorf("erreur chargement clé privée: %w", err)
	}

	// Récupération de l'adresse publique
	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		return nil, fmt.Errorf("erreur conversion clé publique")
	}
	address := crypto.PubkeyToAddress(*publicKeyECDSA)

	// Chain ID pour Sepolia (11155111)
	chainID := big.NewInt(11155111)

	// Vérification du solde
	balance, err := client.BalanceAt(context.Background(), address, nil)
	if err != nil {
		log.Printf("⚠️ Impossible de vérifier le solde: %v", err)
	} else {
		ethBalance := new(big.Float).Quo(new(big.Float).SetInt(balance), big.NewFloat(1e18))
		log.Printf("✅ Connecté à Sepolia - Balance: %s ETH", ethBalance.Text('f', 6))
	}

	log.Printf("✅ Auditeur blockchain initialisé")
	log.Printf("   Réseau: Ethereum Sepolia Testnet")
	log.Printf("   Adresse: %s", address.Hex())
	log.Printf("   Chain ID: %d", chainID.Int64())

	return &BlockchainAuditor{
		client:     client,
		privateKey: privateKey,
		address:    address,
		chainID:    chainID,
		ctx:        context.Background(),
		enabled:    true,
	}, nil
}

// RecordTrade enregistre un trade sur la blockchain Sepolia
func (ba *BlockchainAuditor) RecordTrade(trade interface{}) (string, error) {
	if !ba.enabled {
		// Si blockchain désactivée, retourner un hash simulé
		return ba.generateMockHash(trade), nil
	}

	// Conversion du trade en JSON
	tradeJSON, err := json.Marshal(trade)
	if err != nil {
		return "", fmt.Errorf("erreur sérialisation trade: %w", err)
	}

	// Création du hash du trade
	hash := ba.hashData(tradeJSON)

	// Envoi d'une transaction avec le hash en data
	txHash, err := ba.sendTransaction(hash)
	if err != nil {
		return "", fmt.Errorf("erreur envoi transaction: %w", err)
	}

	log.Printf("⛓️  Trade enregistré sur blockchain")
	log.Printf("   TX Hash: %s", txHash)
	log.Printf("   Voir: https://sepolia.etherscan.io/tx/%s", txHash)

	return txHash, nil
}

// sendTransaction envoie une transaction sur Sepolia
func (ba *BlockchainAuditor) sendTransaction(data []byte) (string, error) {
	// Récupération du nonce
	nonce, err := ba.client.PendingNonceAt(ba.ctx, ba.address)
	if err != nil {
		return "", fmt.Errorf("erreur récupération nonce: %w", err)
	}

	// Estimation du gas price
	gasPrice, err := ba.client.SuggestGasPrice(ba.ctx)
	if err != nil {
		return "", fmt.Errorf("erreur récupération gas price: %w", err)
	}

	// Augmentation du gas price de 20% pour être sûr
	gasPrice = new(big.Int).Mul(gasPrice, big.NewInt(12))
	gasPrice = new(big.Int).Div(gasPrice, big.NewInt(10))

	// Limite de gas
	gasLimit := uint64(100000) // Suffisant pour une transaction simple avec data

	// Valeur à envoyer (0 ETH, on envoie juste la data)
	value := big.NewInt(0)

	// Création de la transaction
	tx := types.NewTransaction(nonce, ba.address, value, gasLimit, gasPrice, data)

	// Signature de la transaction
	signedTx, err := types.SignTx(tx, types.NewEIP155Signer(ba.chainID), ba.privateKey)
	if err != nil {
		return "", fmt.Errorf("erreur signature transaction: %w", err)
	}

	// Envoi de la transaction
	err = ba.client.SendTransaction(ba.ctx, signedTx)
	if err != nil {
		return "", fmt.Errorf("erreur envoi transaction: %w", err)
	}

	return signedTx.Hash().Hex(), nil
}

// hashData crée un hash SHA-256 des données
func (ba *BlockchainAuditor) hashData(data []byte) []byte {
	hash := sha256.Sum256(data)
	return hash[:]
}

// generateMockHash génère un hash simulé (quand blockchain désactivée)
func (ba *BlockchainAuditor) generateMockHash(trade interface{}) string {
	tradeJSON, _ := json.Marshal(trade)
	hash := sha256.Sum256(tradeJSON)
	return "0xMOCK" + hex.EncodeToString(hash[:16])
}

// GetTransactionReceipt récupère le reçu d'une transaction
func (ba *BlockchainAuditor) GetTransactionReceipt(txHash string) (*types.Receipt, error) {
	if !ba.enabled {
		return nil, fmt.Errorf("blockchain désactivée")
	}

	hash := common.HexToHash(txHash)
	receipt, err := ba.client.TransactionReceipt(ba.ctx, hash)
	if err != nil {
		return nil, err
	}

	return receipt, nil
}

// WaitForConfirmation attend la confirmation d'une transaction
func (ba *BlockchainAuditor) WaitForConfirmation(txHash string, timeout time.Duration) error {
	if !ba.enabled {
		return nil
	}

	hash := common.HexToHash(txHash)
	ctx, cancel := context.WithTimeout(ba.ctx, timeout)
	defer cancel()

	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return fmt.Errorf("timeout en attente de confirmation")
		case <-ticker.C:
			receipt, err := ba.client.TransactionReceipt(ctx, hash)
			if err == nil && receipt != nil {
				if receipt.Status == types.ReceiptStatusSuccessful {
					log.Printf("✅ Transaction confirmée: %s (block %d)",
						txHash, receipt.BlockNumber.Uint64())
					return nil
				}
				return fmt.Errorf("transaction échouée")
			}
		}
	}
}

// GetBalance récupère le solde ETH du compte
func (ba *BlockchainAuditor) GetBalance() (*big.Float, error) {
	if !ba.enabled {
		return big.NewFloat(0), nil
	}

	balance, err := ba.client.BalanceAt(ba.ctx, ba.address, nil)
	if err != nil {
		return nil, err
	}

	ethBalance := new(big.Float).Quo(new(big.Float).SetInt(balance), big.NewFloat(1e18))
	return ethBalance, nil
}

// IsEnabled retourne si la blockchain est activée
func (ba *BlockchainAuditor) IsEnabled() bool {
	return ba.enabled
}

// Close ferme la connexion au client Ethereum
func (ba *BlockchainAuditor) Close() {
	if ba.client != nil {
		ba.client.Close()
	}
}

// GetExplorerURL retourne l'URL Etherscan pour une transaction
func (ba *BlockchainAuditor) GetExplorerURL(txHash string) string {
	return fmt.Sprintf("https://sepolia.etherscan.io/tx/%s", txHash)
}

// VerifyTrade vérifie qu'un trade existe sur la blockchain
func (ba *BlockchainAuditor) VerifyTrade(txHash string) (bool, error) {
	if !ba.enabled {
		// En mode mock, on accepte tous les hashes qui commencent par 0xMOCK
		return len(txHash) > 6 && txHash[:6] == "0xMOCK", nil
	}

	receipt, err := ba.GetTransactionReceipt(txHash)
	if err != nil {
		return false, err
	}

	return receipt.Status == types.ReceiptStatusSuccessful, nil
}
