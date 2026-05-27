// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title LumenScoringRegistry
/// @notice On-chain credit ratings for AI agents on Mantle, built on top of ERC-8004.
/// @dev Reads from official ERC-8004 IdentityRegistry & ReputationRegistry,
///      publishes verifiable Lumen Scores. Like Bloomberg credit ratings, but trustless.
contract LumenScoringRegistry is AccessControl, ReentrancyGuard, Pausable {
    // ============================================================
    // Constants
    // ============================================================

    /// @notice Role for backend services authorized to publish scores
    bytes32 public constant SCORER_ROLE = keccak256("SCORER_ROLE");

    /// @notice Official ERC-8004 IdentityRegistry on Mantle Mainnet
    address public constant IDENTITY_REGISTRY = 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432;

    /// @notice Official ERC-8004 ReputationRegistry on Mantle Mainnet
    address public constant REPUTATION_REGISTRY = 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63;

    /// @notice Score must be between 0 and 100
    uint16 public constant MAX_SCORE = 100;

    // ============================================================
    // Types
    // ============================================================

    enum RiskLevel { SAFE, SUSPICIOUS, SYBIL }

    struct LumenScore {
        uint16 score;              // 0-100
        uint8 grade;               // 0=F, 1=D, 2=C, 3=B, 4=A
        RiskLevel risk;            // SAFE / SUSPICIOUS / SYBIL
        uint64 updatedAt;          // block.timestamp
        bytes32 analysisHash;      // keccak256 of analyst note (IPFS verification)
        string analysisURI;        // IPFS or HTTPS URI to full analyst note
    }

    // ============================================================
    // Storage
    // ============================================================

    /// @notice Lumen scores keyed by ERC-8004 agentId
    mapping(uint256 => LumenScore) private _scores;

    /// @notice Tracks which agentIds have ever been scored
    mapping(uint256 => bool) public hasScore;

    /// @notice Count of scored agents (for stats)
    uint256 public scoredAgentCount;

    // ============================================================
    // Events
    // ============================================================

    event ScoreUpdated(
        uint256 indexed agentId,
        uint16 score,
        uint8 grade,
        RiskLevel risk,
        string analysisURI
    );

    event ScamAlert(
        uint256 indexed agentId,
        string reason,
        uint64 detectedAt
    );

    event ScorerGranted(address indexed account);
    event ScorerRevoked(address indexed account);

    // ============================================================
    // Errors
    // ============================================================

    error ScoreOutOfRange(uint16 score);
    error InvalidGrade(uint8 grade);
    error EmptyAnalysisURI();
    error AgentIdZero();

    // ============================================================
    // Constructor
    // ============================================================

    constructor(address admin) {
        require(admin != address(0), "admin = zero");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SCORER_ROLE, admin);
    }

    // ============================================================
    // Admin: scorer management
    // ============================================================

    function grantScorer(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(account != address(0), "account = zero");
        _grantRole(SCORER_ROLE, account);
        emit ScorerGranted(account);
    }

    function revokeScorer(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _revokeRole(SCORER_ROLE, account);
        emit ScorerRevoked(account);
    }

    // ============================================================
    // Admin: emergency pause
    // ============================================================

    /// @notice Pause all score updates (emergency use)
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    /// @notice Resume score updates after pause
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    // ============================================================
    // Core: publish score
    // ============================================================

    /// @notice Publish or update an agent's Lumen Score
    /// @dev Only callable by accounts with SCORER_ROLE when not paused
    function updateScore(
        uint256 agentId,
        uint16 score,
        uint8 grade,
        RiskLevel risk,
        string calldata analysisURI,
        bytes32 analysisHash
    ) external onlyRole(SCORER_ROLE) nonReentrant whenNotPaused {
        if (score > MAX_SCORE) revert ScoreOutOfRange(score);
        if (grade > 4) revert InvalidGrade(grade);
        if (bytes(analysisURI).length == 0) revert EmptyAnalysisURI();

        _scores[agentId] = LumenScore({
            score: score,
            grade: grade,
            risk: risk,
            updatedAt: uint64(block.timestamp),
            analysisHash: analysisHash,
            analysisURI: analysisURI
        });

        if (!hasScore[agentId]) {
            hasScore[agentId] = true;
            scoredAgentCount++;
        }

        emit ScoreUpdated(agentId, score, grade, risk, analysisURI);

        if (risk == RiskLevel.SYBIL) {
            emit ScamAlert(agentId, "Sybil cluster detected", uint64(block.timestamp));
        }
    }

    /// @notice Batch update for gas efficiency
    function batchUpdateScores(
        uint256[] calldata agentIds,
        uint16[] calldata scores,
        uint8[] calldata grades,
        RiskLevel[] calldata risks,
        string[] calldata analysisURIs,
        bytes32[] calldata analysisHashes
    ) external onlyRole(SCORER_ROLE) nonReentrant whenNotPaused {
        uint256 len = agentIds.length;
        require(
            scores.length == len &&
            grades.length == len &&
            risks.length == len &&
            analysisURIs.length == len &&
            analysisHashes.length == len,
            "length mismatch"
        );
        require(len <= 50, "batch too large");

        for (uint256 i = 0; i < len; i++) {
            uint16 s = scores[i];
            uint8 g = grades[i];
            if (s > MAX_SCORE) revert ScoreOutOfRange(s);
            if (g > 4) revert InvalidGrade(g);
            if (bytes(analysisURIs[i]).length == 0) revert EmptyAnalysisURI();

            uint256 aid = agentIds[i];
            _scores[aid] = LumenScore({
                score: s,
                grade: g,
                risk: risks[i],
                updatedAt: uint64(block.timestamp),
                analysisHash: analysisHashes[i],
                analysisURI: analysisURIs[i]
            });

            if (!hasScore[aid]) {
                hasScore[aid] = true;
                scoredAgentCount++;
            }

            emit ScoreUpdated(aid, s, g, risks[i], analysisURIs[i]);

            if (risks[i] == RiskLevel.SYBIL) {
                emit ScamAlert(aid, "Sybil cluster detected", uint64(block.timestamp));
            }
        }
    }

    // ============================================================
    // Read functions (anyone can query)
    // ============================================================

    function getScore(uint256 agentId) external view returns (LumenScore memory) {
        return _scores[agentId];
    }

    function getScoreCompact(uint256 agentId)
        external
        view
        returns (uint16 score, uint8 grade, RiskLevel risk, uint64 updatedAt)
    {
        LumenScore storage s = _scores[agentId];
        return (s.score, s.grade, s.risk, s.updatedAt);
    }

    function isSybil(uint256 agentId) external view returns (bool) {
        return _scores[agentId].risk == RiskLevel.SYBIL;
    }

    function verifyAnalysis(uint256 agentId, bytes32 contentHash) external view returns (bool) {
        return _scores[agentId].analysisHash == contentHash;
    }
}