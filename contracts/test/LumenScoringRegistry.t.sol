// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {LumenScoringRegistry} from "../src/LumenScoringRegistry.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";

contract LumenScoringRegistryTest is Test {
    LumenScoringRegistry public registry;
    address public admin = address(0xA11CE);
    address public scorer = address(0xB0B);
    address public attacker = address(0xBAD0);

    function setUp() public {
        registry = new LumenScoringRegistry(admin);
        vm.prank(admin);
        registry.grantScorer(scorer);
    }

    // ---------- Happy path ----------

    function test_UpdateScore_Works() public {
        vm.prank(scorer);
        registry.updateScore(
            95,
            69,
            3,
            LumenScoringRegistry.RiskLevel.SAFE,
            "ipfs://Qm.../note.json",
            keccak256("note content")
        );

        (uint16 s, uint8 g, LumenScoringRegistry.RiskLevel r,) = registry.getScoreCompact(95);
        assertEq(s, 69);
        assertEq(g, 3);
        assertEq(uint8(r), uint8(LumenScoringRegistry.RiskLevel.SAFE));
        assertEq(registry.scoredAgentCount(), 1);
    }

    function test_ScamAlert_OnSybil() public {
        vm.prank(scorer);
        vm.expectEmit(true, false, false, true);
        emit LumenScoringRegistry.ScamAlert(
            2,
            "Sybil cluster detected",
            uint64(block.timestamp)
        );

        registry.updateScore(
            2,
            11,
            0,
            LumenScoringRegistry.RiskLevel.SYBIL,
            "ipfs://Qm.../sybil.json",
            keccak256("sybil")
        );
    }

    // ---------- Security tests ----------

    function test_RevertWhen_NotScorer() public {
    vm.expectRevert();
    vm.prank(attacker);
    registry.updateScore(1, 50, 2, LumenScoringRegistry.RiskLevel.SAFE, "x", bytes32(0));
    }

    function test_RevertWhen_ScoreOutOfRange() public {
        vm.prank(scorer);
        vm.expectRevert(
            abi.encodeWithSelector(LumenScoringRegistry.ScoreOutOfRange.selector, 101)
        );
        registry.updateScore(1, 101, 2, LumenScoringRegistry.RiskLevel.SAFE, "x", bytes32(0));
    }

    function test_RevertWhen_GradeInvalid() public {
        vm.prank(scorer);
        vm.expectRevert(
            abi.encodeWithSelector(LumenScoringRegistry.InvalidGrade.selector, 5)
        );
        registry.updateScore(1, 50, 5, LumenScoringRegistry.RiskLevel.SAFE, "x", bytes32(0));
    }

    function test_RevertWhen_EmptyURI() public {
        vm.prank(scorer);
        vm.expectRevert(LumenScoringRegistry.EmptyAnalysisURI.selector);
        registry.updateScore(1, 50, 2, LumenScoringRegistry.RiskLevel.SAFE, "", bytes32(0));
    }

    // ---------- Batch ----------

    function test_BatchUpdate_Works() public {
        uint256[] memory ids = new uint256[](3);
        uint16[] memory scores = new uint16[](3);
        uint8[] memory grades = new uint8[](3);
        LumenScoringRegistry.RiskLevel[] memory risks = new LumenScoringRegistry.RiskLevel[](3);
        string[] memory uris = new string[](3);
        bytes32[] memory hashes = new bytes32[](3);

        for (uint256 i = 0; i < 3; i++) {
            ids[i] = i;
            scores[i] = uint16(50 + i);
            grades[i] = 2;
            risks[i] = LumenScoringRegistry.RiskLevel.SAFE;
            uris[i] = "ipfs://test";
            hashes[i] = keccak256(abi.encode(i));
        }

        vm.prank(scorer);
        registry.batchUpdateScores(ids, scores, grades, risks, uris, hashes);

        assertEq(registry.scoredAgentCount(), 3);
    }

    function test_RevertWhen_BatchTooLarge() public {
        uint256[] memory ids = new uint256[](51);
        uint16[] memory scores = new uint16[](51);
        uint8[] memory grades = new uint8[](51);
        LumenScoringRegistry.RiskLevel[] memory risks = new LumenScoringRegistry.RiskLevel[](51);
        string[] memory uris = new string[](51);
        bytes32[] memory hashes = new bytes32[](51);

        vm.prank(scorer);
        vm.expectRevert(bytes("batch too large"));
        registry.batchUpdateScores(ids, scores, grades, risks, uris, hashes);
    }

    // ---------- Admin ----------

    function test_GrantAndRevokeScorer() public {
        address newScorer = address(0xCAFE);

        vm.prank(admin);
        registry.grantScorer(newScorer);
        assertTrue(registry.hasRole(registry.SCORER_ROLE(), newScorer));

        vm.prank(admin);
        registry.revokeScorer(newScorer);
        assertFalse(registry.hasRole(registry.SCORER_ROLE(), newScorer));
    }

    function test_RevertWhen_NonAdminGrantsScorer() public {
        vm.prank(attacker);
        vm.expectRevert();
        registry.grantScorer(address(0xCAFE));
    }

    // ---------- Verify ----------

    function test_VerifyAnalysisHash() public {
        bytes32 hash = keccak256("the real note");
        vm.prank(scorer);
        registry.updateScore(1, 80, 4, LumenScoringRegistry.RiskLevel.SAFE, "x", hash);

        assertTrue(registry.verifyAnalysis(1, hash));
        assertFalse(registry.verifyAnalysis(1, keccak256("fake")));
    }

    // ---------- Pausable ----------

    function test_PauseBlocksUpdates() public {
        vm.prank(admin);
        registry.pause();

        vm.prank(scorer);
        vm.expectRevert();
        registry.updateScore(1, 50, 2, LumenScoringRegistry.RiskLevel.SAFE, "x", bytes32(0));
    }

    function test_UnpauseRestoresUpdates() public {
        vm.prank(admin);
        registry.pause();

        vm.prank(admin);
        registry.unpause();

        vm.prank(scorer);
        registry.updateScore(1, 50, 2, LumenScoringRegistry.RiskLevel.SAFE, "x", bytes32(0));
        assertEq(registry.scoredAgentCount(), 1);
    }

    function test_RevertWhen_NonAdminPauses() public {
        vm.prank(attacker);
        vm.expectRevert();
        registry.pause();
    }
}