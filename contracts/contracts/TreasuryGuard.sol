// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract TreasuryGuard is AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant EXECUTOR_ROLE = keccak256("EXECUTOR_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");
    uint256 public immutable maxSinglePaymentUnits;
    uint256 public dailyLimitUnits;

    mapping(address => bool) public allowedTokens;
    mapping(address => bool) public allowedRecipients;
    mapping(bytes32 => bool) public paidInvoiceHashes;
    mapping(bytes32 => uint256) public vendorLimitUnits;
    mapping(bytes32 => uint256) public vendorSpentUnits;
    mapping(uint256 => uint256) public spentByDay;

    event TokenAllowed(address indexed token, bool allowed);
    event RecipientAllowed(address indexed recipient, bool allowed);
    event VendorLimitSet(bytes32 indexed vendorId, uint256 limitUnits);
    event PaymentExecuted(
        bytes32 indexed invoiceHash,
        address indexed token,
        address indexed recipient,
        uint256 amount,
        bytes32 vendorId,
        bytes32 decisionHash
    );

    error TokenNotAllowed(address token);
    error RecipientNotAllowed(address recipient);
    error PaymentTooLarge(uint256 amount);
    error DailyLimitExceeded(uint256 nextSpent, uint256 limit);
    error VendorLimitExceeded(bytes32 vendorId, uint256 nextSpent, uint256 limit);
    error InvoiceAlreadyPaid(bytes32 invoiceHash);

    constructor(address admin, uint256 maxSinglePaymentUnits_) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(EXECUTOR_ROLE, admin);
        _grantRole(GUARDIAN_ROLE, admin);
        maxSinglePaymentUnits = maxSinglePaymentUnits_;
        dailyLimitUnits = maxSinglePaymentUnits_ * 4;
    }

    function setTokenAllowed(address token, bool allowed)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        allowedTokens[token] = allowed;
        emit TokenAllowed(token, allowed);
    }

    function setRecipientAllowed(address recipient, bool allowed)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        allowedRecipients[recipient] = allowed;
        emit RecipientAllowed(recipient, allowed);
    }

    function setDailyLimit(uint256 limitUnits) external onlyRole(DEFAULT_ADMIN_ROLE) {
        dailyLimitUnits = limitUnits;
    }

    function setVendorLimit(bytes32 vendorId, uint256 limitUnits)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        vendorLimitUnits[vendorId] = limitUnits;
        emit VendorLimitSet(vendorId, limitUnits);
    }

    function pause() external onlyRole(GUARDIAN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function executePayment(
        IERC20 token,
        address recipient,
        uint256 amount,
        bytes32 invoiceHash,
        bytes32 decisionHash
    ) external {
        executePaymentWithVendor(token, recipient, amount, invoiceHash, bytes32(0), decisionHash);
    }

    function executePaymentWithVendor(
        IERC20 token,
        address recipient,
        uint256 amount,
        bytes32 invoiceHash,
        bytes32 vendorId,
        bytes32 decisionHash
    ) public onlyRole(EXECUTOR_ROLE) whenNotPaused nonReentrant {
        if (!allowedTokens[address(token)]) revert TokenNotAllowed(address(token));
        if (!allowedRecipients[recipient]) revert RecipientNotAllowed(recipient);
        if (amount > maxSinglePaymentUnits) revert PaymentTooLarge(amount);
        if (paidInvoiceHashes[invoiceHash]) revert InvoiceAlreadyPaid(invoiceHash);

        uint256 day = block.timestamp / 1 days;
        uint256 nextDailySpent = spentByDay[day] + amount;
        if (nextDailySpent > dailyLimitUnits) revert DailyLimitExceeded(nextDailySpent, dailyLimitUnits);

        uint256 vendorLimit = vendorLimitUnits[vendorId];
        uint256 nextVendorSpent = vendorSpentUnits[vendorId] + amount;
        if (vendorLimit != 0 && nextVendorSpent > vendorLimit) {
            revert VendorLimitExceeded(vendorId, nextVendorSpent, vendorLimit);
        }

        paidInvoiceHashes[invoiceHash] = true;
        spentByDay[day] = nextDailySpent;
        vendorSpentUnits[vendorId] = nextVendorSpent;
        token.safeTransfer(recipient, amount);
        emit PaymentExecuted(invoiceHash, address(token), recipient, amount, vendorId, decisionHash);
    }
}
