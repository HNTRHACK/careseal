# CARESEAL — SMART CONTRACT ARCHITECTURE SPECIFICATION

**Target Network:** Arc Testnet (Chain ID: `5042002` / `0x4cef52`)  
**Contract Name:** `CareSealEscrow.sol`  
**Framework:** OpenZeppelin Contracts v5, Foundry, Arc Studio  
**Coordination Directive:** Final ABI and bytecode will be coordinated with the Arc Studio implementation in Phase 01. No speculative ABI is prematurely frozen.

---

## 1. Network & Token Configuration

| Parameter | Value | Critical Specification |
|---|---|---|
| **Network Name** | Arc Testnet | Circle Layer-1 EVM test network |
| **Chain ID** | `5042002` (`0x4cef52`) | Verified official Arc Testnet identifier |
| **RPC Endpoint** | `https://rpc.testnet.arc.network` | Primary RPC endpoint |
| **Explorer** | `https://testnet.arcscan.app` | Verification and transaction trace explorer |
| **Native Gas Token** | `USDC` | **18 decimals** internal EVM gas layer |
| **Escrow Application Token** | `USDC` (ERC-20) | **6 decimals** (`1 USDC = 1,000,000 micro-units`) |
| **Decimals Invariant** | Non-conflation | Never mix native value transfers (`msg.value`) with ERC-20 token transfers (`SafeERC20`) |

---

## 2. Core Invariants & Privilege Ceilings

1. **Privilege Ceiling:** No owner, admin, or guardian address possesses unrestricted withdrawal authority or arbitrary token rescue sweeps. Escrow funds can only exit via legitimate settlement or donor refund.
2. **Frozen Hospital Payee:** The `hospitalPayee` address is set at claim registration and is permanently immutable. No party may redirect payout proceeds.
3. **Dual Reviewer Separation:** Medical and Financial approvals must originate from distinct authorized reviewer organizations, and neither reviewer may belong to the issuing hospital.
4. **Hard Funding Cap:** Cumulative contributions (`raisedAmountTokenUnits`) cannot exceed the registered `maxAmountTokenUnits`. Any deposit attempting to exceed the cap reverts.
5. **Atomic Single Settlement:** Funds release exactly once to the frozen `hospitalPayee` upon verified milestone confirmation.
6. **Pull-Based Donor Refunds:** If a claim expires or is cancelled before settlement, donors withdraw their recorded balance directly. Double refunds and cross-donor balance claims are impossible.
7. **Conservation of Balance:** At all times, `token.balanceOf(address(this)) == sum(unsettled deposits) - refunds - settlements`.
8. **Emergency Pause:** A security guardian can pause new registrations and deposits during an incident, but pause semantics cannot trap eligible donor refunds.

---

## 3. Data Structures & State Machine

```solidity
enum ClaimStatus {
    DRAFT,
    REGISTERED,
    FUNDING,
    FUNDED,
    MILESTONE_APPROVED,
    SETTLED,
    CANCELLED,
    EXPIRED
}

struct Claim {
    bytes32 commitment;
    address hospitalPayee;
    uint256 maxAmountTokenUnits; // 6 decimals (test USDC micro-units)
    uint256 raisedAmountTokenUnits;
    uint64 registeredAt;
    uint64 expiresAt;
    bool medicalApproved;
    bool financialApproved;
    bool milestoneApproved;
    ClaimStatus status;
}
```

---

## 4. Required Methods & Interface Alignment

```solidity
interface ICareSealEscrow {
    // Claim Lifecycle
    function registerClaim(
        bytes32 commitment,
        address hospitalPayee,
        uint256 maxAmountTokenUnits,
        uint64 expiresAt
    ) external returns (bytes32 claimId);

    // Dual Review Approvals
    function approveMedical(bytes32 claimId) external;
    function approveFinancial(bytes32 claimId) external;

    // Funder Operations
    function contribute(bytes32 claimId, uint256 amountTokenUnits) external;
    function claimRefund(bytes32 claimId) external;

    // Milestone & Settlement
    function confirmMilestone(bytes32 claimId) external;
    function settle(bytes32 claimId) external;

    // Administrative / Guardian
    function cancelClaim(bytes32 claimId, string calldata reason) external;
    function pause() external;
    function unpause() external;
}
```

---

## 5. Phase 01 Arc Studio Workflow Alignment

- **Arc Studio Origin:** Arc Studio (`https://studio.arc.io/`) is the designated starting point for the prize-relevant contract implementation.
- **Claude Ownership:** Claude will coordinate the contract implementation between Arc Studio and `contracts/src/CareSealEscrow.sol`.
- **Foundry Validation:** Foundry will independently test the exported contract against unit, fuzz, reentrancy, overfund, and invariant test suites before deployment to Arc Testnet.

