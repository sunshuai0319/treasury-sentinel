// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract TreasuryGuard is AccessControl, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant EXECUTOR_ROLE = keccak256("EXECUTOR_ROLE");
    uint256 public immutable maxSinglePaymentUnits;

    mapping(address => bool) public allowedRecipients;
    mapping(bytes32 => bool) public paidInvoiceHashes;

    event RecipientAllowed(address indexed recipient, bool allowed);
    event PaymentExecuted(
        bytes32 indexed invoiceHash,
        address indexed token,
        address indexed recipient,
        uint256 amount,
        bytes32 decisionHash
    );

    error RecipientNotAllowed(address recipient);
    error PaymentTooLarge(uint256 amount);
    error InvoiceAlreadyPaid(bytes32 invoiceHash);

    constructor(address admin, uint256 maxSinglePaymentUnits_) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(EXECUTOR_ROLE, admin);
        maxSinglePaymentUnits = maxSinglePaymentUnits_;
    }

    function setRecipientAllowed(address recipient, bool allowed)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        allowedRecipients[recipient] = allowed;
        emit RecipientAllowed(recipient, allowed);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
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
    ) external onlyRole(EXECUTOR_ROLE) whenNotPaused {
        if (!allowedRecipients[recipient]) revert RecipientNotAllowed(recipient);
        if (amount > maxSinglePaymentUnits) revert PaymentTooLarge(amount);
        if (paidInvoiceHashes[invoiceHash]) revert InvoiceAlreadyPaid(invoiceHash);

        paidInvoiceHashes[invoiceHash] = true;
        token.safeTransfer(recipient, amount);
        emit PaymentExecuted(invoiceHash, address(token), recipient, amount, decisionHash);
    }
}

