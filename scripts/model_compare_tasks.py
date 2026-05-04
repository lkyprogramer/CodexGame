#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable


COMMON_DEVELOPER_MESSAGE = dedent(
    """\
    You are a senior software engineer performing a real coding review.

    Use only the provided project snapshot.
    Focus on correctness, root cause, and the smallest safe fix.
    Prefer minimal changes over rewrites.
    Call out exact files that should change.
    End with concise regression checks.
    If the snapshot is insufficient, say exactly what is missing instead of inventing APIs.
    """
).strip()


@dataclass(frozen=True)
class ContextFile:
    display_path: str
    inline_content: str | None = None
    repo_path: str | None = None
    generated_content: Callable[[Path], str] | None = None

    def load_content(self, repo_root: Path) -> str:
        if self.inline_content is not None:
            return self.inline_content.strip() + "\n"
        if self.generated_content is not None:
            return self.generated_content(repo_root).rstrip() + "\n"
        if self.repo_path is None:
            raise ValueError(f"Context file {self.display_path} has no content source")
        return (repo_root / self.repo_path).read_text(encoding="utf-8")


@dataclass(frozen=True)
class CompareTask:
    task_id: str
    family: str
    description: str
    developer_message: str
    user_request: str
    max_tokens: int
    context_files: tuple[ContextFile, ...]
    hidden_checklist: tuple[str, ...]
    repeat_group: str | None = None

    def render_user_message(self, repo_root: Path) -> str:
        parts = [
            f"Task ID: {self.task_id}",
            f"Scenario: {self.description}",
            "",
            "Instructions:",
            self.user_request.strip(),
            "",
            "Project snapshot:",
        ]
        for file in self.context_files:
            parts.append("")
            parts.append(f"=== File: {file.display_path} ===")
            parts.append(file.load_content(repo_root).rstrip())
        return "\n".join(parts).strip() + "\n"

    def to_manifest_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "family": self.family,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "repeat_group": self.repeat_group,
            "developer_message": self.developer_message,
            "user_request": self.user_request,
            "context_files": [f.display_path for f in self.context_files],
            "hidden_checklist": list(self.hidden_checklist),
        }


def _java_file(path: str, content: str) -> ContextFile:
    return ContextFile(display_path=path, inline_content=dedent(content).strip())


def _repo_file(path: str) -> ContextFile:
    return ContextFile(display_path=path, repo_path=path)


def _generated_file(path: str, factory: Callable[[Path], str]) -> ContextFile:
    return ContextFile(display_path=path, generated_content=factory)


SCRIPT_DEVELOPER_MESSAGE = dedent(
    """\
    You are a senior software engineer solving a real production task.

    Use only the provided project snapshot and operational context.
    Prefer the smallest safe script or patch over a broad rewrite.
    If you propose a script, make it production-safe, explicit, and reviewable.
    Call out exact files, commands, or script sections that should change.
    End with concise verification checks.
    """
).strip()


def _repeat_block(title: str, block: str, repeat: int) -> str:
    section = dedent(block).strip()
    parts: list[str] = []
    for index in range(1, repeat + 1):
        parts.append(f"# {title} {index}")
        parts.append(section)
    return "\n\n".join(parts)


def _extreme_restore_context(repo_root: Path) -> str:
    files = [
        "apps/game-runtime/src/runtime/GameRuntimeServer.ts",
        "apps/game-runtime/src/runtime/stateStore.ts",
        "apps/game-runtime/src/runtime/replay.ts",
        "apps/game-runtime/src/runtime/types.ts",
        "apps/game-runtime/src/runtime/contentStore.ts",
        "packages/protocol/src/messages.ts",
        "apps/game-runtime/test/ui-contract.integration.test.ts",
    ]
    chunks = [
        f"=== File: {path} ===\n{(repo_root / path).read_text(encoding='utf-8').rstrip()}"
        for path in files
    ]
    synthetic_log = _repeat_block(
        "restore-incident-log",
        """
        2026-03-08T09:00:01Z INFO restoreSession loaded simulation tick=1245 agents=3
        2026-03-08T09:00:01Z INFO phase=running preparedSeed=null connected=false threadIds={}
        2026-03-08T09:00:01Z WARN scheduler skipped agent turn because gameplay thread missing
        2026-03-08T09:00:02Z INFO model catalog refresh started
        2026-03-08T09:00:02Z INFO thread bootstrap requested for agent-1
        2026-03-08T09:00:02Z INFO thread bootstrap requested for agent-2
        2026-03-08T09:00:02Z INFO thread bootstrap requested for agent-3
        2026-03-08T09:00:03Z WARN client observed session.state phase=running while no thread ids were present
        """,
        700,
    )
    return "\n\n".join(chunks + ["=== File: logs/restore-incident.log ===", synthetic_log])


def _extreme_metrics_context(repo_root: Path) -> str:
    files = [
        "apps/game-runtime/src/runtime/metrics.ts",
        "apps/game-runtime/src/runtime/GameRuntimeServer.ts",
        "packages/protocol/src/messages.ts",
        "apps/game-client/src/App.tsx",
        "apps/game-client/src/components/GodConsoleSidebar.tsx",
        "apps/game-runtime/test/ui-contract.integration.test.ts",
    ]
    chunks = [
        f"=== File: {path} ===\n{(repo_root / path).read_text(encoding='utf-8').rstrip()}"
        for path in files
    ]
    synthetic_log = _repeat_block(
        "runtime-metrics-snapshots",
        """
        {"tick": 1201, "queuedActions": 3, "invalidOutputCount": 5, "actionAppliedCount": 410, "actionRejectedCount": 29, "turnsTotal": 88}
        {"tick": 1202, "queuedActions": 1, "invalidOutputCount": 5, "actionAppliedCount": 411, "actionRejectedCount": 29, "turnsTotal": 89}
        {"tick": 1203, "queuedActions": 0, "invalidOutputCount": 6, "actionAppliedCount": 412, "actionRejectedCount": 29, "turnsTotal": 90}
        {"tick": 1204, "queuedActions": 4, "invalidOutputCount": 6, "actionAppliedCount": 412, "actionRejectedCount": 30, "turnsTotal": 90}
        """,
        760,
    )
    return "\n\n".join(chunks + ["=== File: logs/runtime-metrics.jsonl ===", synthetic_log])


def _extreme_java_context(_: Path) -> str:
    repeated_service = _repeat_block(
        "src/main/java/com/example/order/OrderApprovalService.java",
        """
        package com.example.order;

        import java.time.Instant;

        public class OrderApprovalService {
            private final OrderRepository orderRepository;
            private final AuditRepository auditRepository;
            private final NotificationGateway notificationGateway;

            public OrderApprovalService(
                    OrderRepository orderRepository,
                    AuditRepository auditRepository,
                    NotificationGateway notificationGateway) {
                this.orderRepository = orderRepository;
                this.auditRepository = auditRepository;
                this.notificationGateway = notificationGateway;
            }

            public void approve(long orderId, String operator) {
                Order order = orderRepository.require(orderId);
                order.setStatus("APPROVED");
                orderRepository.save(order);
                notificationGateway.sendApproval(orderId, operator);
                auditRepository.record("ORDER_APPROVED", orderId, Instant.now());
            }
        }
        """,
        560,
    )
    repeated_log = _repeat_block(
        "logs/order-approval-failures.log",
        """
        2026-03-08T10:00:01Z INFO approving order=991 operator=alice
        2026-03-08T10:00:01Z WARN notification timeout order=991 operator=alice
        2026-03-08T10:00:01Z INFO retry attempt=2 order=991
        2026-03-08T10:00:02Z INFO duplicate approval email observed order=991 operator=alice
        """,
        640,
    )
    return "\n\n".join([repeated_service, repeated_log])


def _extreme_script_context(_: Path) -> str:
    rules = _repeat_block(
        "docs/reconcile-rules.md",
        """
        - Source A is the finance export of settled payouts.
        - Source B is the merchant statement export.
        - Match rows by merchant_order_id first, then provider_txn_id.
        - Flag amount mismatches, missing rows, duplicate rows, and stale refunds.
        - Emit a machine-readable CSV plus a human-readable summary.
        - The script must tolerate blank cells, BOM headers, and duplicate header rows.
        """,
        1200,
    )
    samples = _repeat_block(
        "samples/reconcile-snippet.csv",
        """
        merchant_order_id,provider_txn_id,amount_cents,status,updated_at
        O-1001,P-9001,12800,SETTLED,2026-03-08T10:00:01Z
        O-1002,P-9002,12800,REFUNDED,2026-03-08T10:05:01Z
        O-1003,P-9003,6500,SETTLED,2026-03-08T10:06:01Z
        O-1003,P-9003,6500,SETTLED,2026-03-08T10:06:01Z
        """,
        1200,
    )
    return "\n\n".join([rules, samples])


def get_tasks() -> list[CompareTask]:
    return [
        CompareTask(
            task_id="java_null_nested_config",
            family="java",
            description="Optional nested config causes startup-time null handling bug.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the highest-risk correctness bug. Explain the root cause and give the smallest "
                "production-safe patch plan. Keep the fix minimal and localized."
            ),
            max_tokens=900,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/config/AppConfig.java",
                    """
                    package com.example.config;

                    public class AppConfig {
                        private DatabaseConfig database;

                        public DatabaseConfig getDatabase() {
                            return database;
                        }

                        public void setDatabase(DatabaseConfig database) {
                            this.database = database;
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/config/DatabaseConfig.java",
                    """
                    package com.example.config;

                    public class DatabaseConfig {
                        private String jdbcUrl;

                        public String getJdbcUrl() {
                            return jdbcUrl;
                        }

                        public void setJdbcUrl(String jdbcUrl) {
                            this.jdbcUrl = jdbcUrl;
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/config/DataSourceFactory.java",
                    """
                    package com.example.config;

                    public class DataSourceFactory {
                        public String buildJdbcUrl(AppConfig config) {
                            return config.getDatabase().getJdbcUrl().trim();
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/bootstrap/StartupListener.java",
                    """
                    package com.example.bootstrap;

                    import com.example.config.AppConfig;
                    import com.example.config.DataSourceFactory;

                    public class StartupListener {
                        private final DataSourceFactory dataSourceFactory = new DataSourceFactory();

                        public void onStartup(AppConfig config) {
                            String jdbcUrl = dataSourceFactory.buildJdbcUrl(config);
                            System.out.println("Connecting to " + jdbcUrl);
                        }
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify null handling risk in config.getDatabase() / getJdbcUrl().",
                "Keep the fix in DataSourceFactory or immediate caller instead of broad rewrites.",
                "Mention trim safety and missing optional config path.",
                "Include startup regression checks for missing database config.",
            ),
        ),
        CompareTask(
            task_id="java_transaction_partial_commit",
            family="java",
            description="Order update spans multiple repositories without a transaction boundary.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Review the update flow and identify the highest-risk data consistency bug. "
                "Propose the smallest safe fix and explain why it is enough."
            ),
            max_tokens=1000,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/order/OrderService.java",
                    """
                    package com.example.order;

                    import java.time.Instant;

                    public class OrderService {
                        private final InventoryRepository inventoryRepository;
                        private final OrderRepository orderRepository;
                        private final AuditRepository auditRepository;

                        public OrderService(
                                InventoryRepository inventoryRepository,
                                OrderRepository orderRepository,
                                AuditRepository auditRepository) {
                            this.inventoryRepository = inventoryRepository;
                            this.orderRepository = orderRepository;
                            this.auditRepository = auditRepository;
                        }

                        public void confirm(long orderId, int quantity) {
                            inventoryRepository.reserve(orderId, quantity);
                            auditRepository.record("ORDER_RESERVED", orderId, Instant.now());
                            orderRepository.markConfirmed(orderId, Instant.now());
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/order/InventoryRepository.java",
                    """
                    package com.example.order;

                    public interface InventoryRepository {
                        void reserve(long orderId, int quantity);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/order/OrderRepository.java",
                    """
                    package com.example.order;

                    import java.time.Instant;

                    public interface OrderRepository {
                        void markConfirmed(long orderId, Instant confirmedAt);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/order/AuditRepository.java",
                    """
                    package com.example.order;

                    import java.time.Instant;

                    public interface AuditRepository {
                        void record(String eventType, long aggregateId, Instant createdAt);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify missing transaction boundary across inventory/order/audit DB writes.",
                "Explain partial commit risk if markConfirmed fails after reserve/audit.",
                "Prefer the minimal fix such as adding a transactional boundary to the service flow.",
                "Mention regression checks for mid-flow failure rollback.",
            ),
        ),
        CompareTask(
            task_id="java_path_body_id_mismatch",
            family="java",
            description="Controller trusts request body identifier over path identifier.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the most dangerous API contract bug and give the minimal fix. "
                "Assume this endpoint is public and used by multiple clients."
            ),
            max_tokens=900,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/account/UpdateAccountRequest.java",
                    """
                    package com.example.account;

                    public class UpdateAccountRequest {
                        private Long accountId;
                        private String displayName;

                        public Long getAccountId() {
                            return accountId;
                        }

                        public void setAccountId(Long accountId) {
                            this.accountId = accountId;
                        }

                        public String getDisplayName() {
                            return displayName;
                        }

                        public void setDisplayName(String displayName) {
                            this.displayName = displayName;
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/account/AccountController.java",
                    """
                    package com.example.account;

                    public class AccountController {
                        private final AccountService accountService;

                        public AccountController(AccountService accountService) {
                            this.accountService = accountService;
                        }

                        public AccountDto update(long pathAccountId, UpdateAccountRequest request) {
                            return accountService.update(request.getAccountId(), request.getDisplayName());
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/account/AccountService.java",
                    """
                    package com.example.account;

                    public class AccountService {
                        private final AccountRepository accountRepository;

                        public AccountService(AccountRepository accountRepository) {
                            this.accountRepository = accountRepository;
                        }

                        public AccountDto update(long accountId, String displayName) {
                            Account account = accountRepository.require(accountId);
                            account.setDisplayName(displayName);
                            accountRepository.save(account);
                            return new AccountDto(account.getId(), account.getDisplayName());
                        }
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify path-vs-body identifier trust bug.",
                "Recommend path variable as source of truth and mismatch validation/removal of body accountId.",
                "Keep fix minimal in controller/request contract instead of wide service rewrite.",
                "Mention regression test for mismatched IDs.",
            ),
        ),
        CompareTask(
            task_id="java_audit_success_on_failure",
            family="java",
            description="Audit log currently records a successful change even when the write fails.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Review the flow and identify the most serious audit consistency bug. "
                "Give the smallest safe patch plan."
            ),
            max_tokens=1000,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/profile/ProfileService.java",
                    """
                    package com.example.profile;

                    public class ProfileService {
                        private final ProfileRepository profileRepository;
                        private final AuditRepository auditRepository;

                        public ProfileService(ProfileRepository profileRepository, AuditRepository auditRepository) {
                            this.profileRepository = profileRepository;
                            this.auditRepository = auditRepository;
                        }

                        public void changeStatus(long profileId, String newStatus) {
                            try {
                                Profile profile = profileRepository.require(profileId);
                                profile.setStatus(newStatus);
                                profileRepository.save(profile);
                            } finally {
                                auditRepository.recordSuccess("PROFILE_STATUS_CHANGED", profileId);
                            }
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/profile/ProfileRepository.java",
                    """
                    package com.example.profile;

                    public interface ProfileRepository {
                        Profile require(long profileId);
                        void save(Profile profile);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/profile/AuditRepository.java",
                    """
                    package com.example.profile;

                    public interface AuditRepository {
                        void recordSuccess(String eventType, long aggregateId);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify that finally always records success even if save throws.",
                "Move success audit after successful persistence or separate success/failure events.",
                "Preserve minimal change rather than redesigning audit subsystem.",
                "Mention regression test for repository save failure.",
            ),
        ),
        CompareTask(
            task_id="java_pagination_boundary",
            family="java",
            description="Pagination code has an index boundary bug and unstable empty-page behavior.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the concrete correctness bug in this pagination flow and propose the smallest patch. "
                "Be explicit about what happens on the last page and on out-of-range requests."
            ),
            max_tokens=900,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/user/UserQueryService.java",
                    """
                    package com.example.user;

                    import java.util.List;

                    public class UserQueryService {
                        private final UserRepository userRepository;

                        public UserQueryService(UserRepository userRepository) {
                            this.userRepository = userRepository;
                        }

                        public List<User> list(int page, int size) {
                            int offset = page * size;
                            return userRepository.findRange(offset, offset + size);
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/user/UserRepository.java",
                    """
                    package com.example.user;

                    import java.util.List;

                    public interface UserRepository {
                        List<User> findRange(int startInclusive, int endInclusive);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/user/InMemoryUserRepository.java",
                    """
                    package com.example.user;

                    import java.util.ArrayList;
                    import java.util.List;

                    public class InMemoryUserRepository implements UserRepository {
                        private final List<User> users = new ArrayList<>();

                        @Override
                        public List<User> findRange(int startInclusive, int endInclusive) {
                            return users.subList(startInclusive, endInclusive);
                        }
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify subList end index is exclusive and may throw when end exceeds size.",
                "Handle offset >= size by returning empty list.",
                "Use minimal boundary clamp such as min(offset + size, users.size()).",
                "Mention tests for last page and out-of-range page.",
            ),
        ),
        CompareTask(
            task_id="java_optimistic_lock_missing",
            family="java",
            description="Version field exists but update flow does not actually enforce optimistic locking.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the concurrency bug and propose the smallest production-safe fix. "
                "Assume this method is hit concurrently from two admin consoles."
            ),
            max_tokens=1050,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/order/Order.java",
                    """
                    package com.example.order;

                    public class Order {
                        private long id;
                        private int version;
                        private String status;

                        public long getId() { return id; }
                        public int getVersion() { return version; }
                        public void setVersion(int version) { this.version = version; }
                        public String getStatus() { return status; }
                        public void setStatus(String status) { this.status = status; }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/order/OrderRepository.java",
                    """
                    package com.example.order;

                    public interface OrderRepository {
                        Order require(long id);
                        void updateStatus(long id, String status, int nextVersion);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/order/OrderService.java",
                    """
                    package com.example.order;

                    public class OrderService {
                        private final OrderRepository orderRepository;

                        public OrderService(OrderRepository orderRepository) {
                            this.orderRepository = orderRepository;
                        }

                        public void approve(long orderId) {
                            Order order = orderRepository.require(orderId);
                            order.setStatus("APPROVED");
                            orderRepository.updateStatus(order.getId(), order.getStatus(), order.getVersion() + 1);
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/order/JdbcOrderRepository.java",
                    """
                    package com.example.order;

                    public class JdbcOrderRepository implements OrderRepository {
                        @Override
                        public Order require(long id) {
                            return null;
                        }

                        @Override
                        public void updateStatus(long id, String status, int nextVersion) {
                            // update orders set status = ?, version = ? where id = ?
                        }
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify version field is ignored in the update predicate.",
                "Recommend update where id and version match, then detect stale update failure.",
                "Keep fix minimal in repository SQL/return contract rather than redesigning service.",
                "Mention concurrent update regression test.",
            ),
        ),
        CompareTask(
            task_id="java_enum_db_compat",
            family="java",
            description="Database enum values no longer match Java enum names after a migration.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the compatibility bug introduced by this migration and suggest the smallest safe patch. "
                "Assume existing production rows already use the migrated values."
            ),
            max_tokens=1000,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/resources/db/migration/V42__payment_state_lowercase.sql",
                    """
                    update payment_record set state = lower(state);
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/PaymentState.java",
                    """
                    package com.example.payment;

                    public enum PaymentState {
                        PENDING,
                        PROCESSING,
                        COMPLETED
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/PaymentRecordDO.java",
                    """
                    package com.example.payment;

                    public class PaymentRecordDO {
                        private String state;

                        public String getState() {
                            return state;
                        }

                        public void setState(String state) {
                            this.state = state;
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/PaymentMapper.java",
                    """
                    package com.example.payment;

                    public class PaymentMapper {
                        public PaymentState toDomain(PaymentRecordDO record) {
                            return PaymentState.valueOf(record.getState());
                        }
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify migration changed DB values to lowercase while valueOf expects enum constant names.",
                "Recommend explicit fromDb mapping or stable code-based mapping.",
                "Keep fix localized to mapper/enum instead of rewriting migration history.",
                "Mention regression coverage for old and new DB values.",
            ),
        ),
        CompareTask(
            task_id="java_soft_delete_unique_email",
            family="java",
            description="Soft-deleted rows still participate in uniqueness checks and block re-registration.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the highest-risk bug in this registration flow and propose the smallest safe fix. "
                "Assume soft-deleted accounts should not block a new registration."
            ),
            max_tokens=950,
            repeat_group="java-core",
            context_files=(
                _java_file(
                    "src/main/java/com/example/user/UserService.java",
                    """
                    package com.example.user;

                    public class UserService {
                        private final UserRepository userRepository;

                        public UserService(UserRepository userRepository) {
                            this.userRepository = userRepository;
                        }

                        public void register(String email) {
                            if (userRepository.existsByEmail(email)) {
                                throw new IllegalArgumentException("email already exists");
                            }
                            userRepository.insert(email);
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/user/UserRepository.java",
                    """
                    package com.example.user;

                    public interface UserRepository {
                        boolean existsByEmail(String email);
                        void insert(String email);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/user/JdbcUserRepository.java",
                    """
                    package com.example.user;

                    public class JdbcUserRepository implements UserRepository {
                        @Override
                        public boolean existsByEmail(String email) {
                            // select count(*) > 0 from users where email = ?
                            return false;
                        }

                        @Override
                        public void insert(String email) {
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/resources/db/migration/V18__add_user_soft_delete.sql",
                    """
                    alter table users add column deleted_at timestamp null;
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify existsByEmail ignores soft delete state.",
                "Recommend filtering active rows only, not a service-layer workaround.",
                "Mention partial unique index or data-level follow-up as optional longer-term hardening.",
                "Include regression for re-registering after soft delete.",
            ),
        ),
        CompareTask(
            task_id="ts_boot_restore_consistency",
            family="ts",
            description="Boot-time restore can expose an inconsistent running state before threads are restored.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Given the real project files below, identify the highest-risk restore consistency bug and propose "
                "the smallest maintainable fix. Preserve atomic persistence and avoid duplicate thread creation."
            ),
            max_tokens=1250,
            repeat_group="ts-core",
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("apps/game-runtime/src/runtime/stateStore.ts"),
                _repo_file("apps/game-runtime/src/runtime/types.ts"),
                _repo_file("packages/protocol/src/messages.ts"),
                _repo_file("apps/game-client/src/App.tsx"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
            ),
            hidden_checklist=(
                "Identify restore path sets a running-visible state before thread restoration is complete.",
                "Mention threadIds restore/bootstrap ordering and idempotent thread recreation.",
                "Respect protocol/client contract instead of patching runtime only.",
                "Preserve stateStore atomic tmp+rename behavior.",
                "Include contract/integration test updates.",
            ),
        ),
        CompareTask(
            task_id="ts_runtime_metrics_protocol",
            family="ts",
            description="Runtime metrics exist server-side but are not exposed to the client in a protocol-first way.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Using the real project files below, propose the smallest protocol-first change set to expose "
                "runtime metrics to the client HUD. Keep simulation authority in runtime and add the right contract tests."
            ),
            max_tokens=1250,
            repeat_group="ts-core",
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/metrics.ts"),
                _repo_file("apps/game-runtime/src/runtime/types.ts"),
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("packages/protocol/src/messages.ts"),
                _repo_file("apps/game-client/src/App.tsx"),
                _repo_file("apps/game-client/src/components/GodConsoleSidebar.tsx"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
            ),
            hidden_checklist=(
                "Start from protocol messages rather than ad-hoc runtime/client fields.",
                "Use MetricsTracker.snapshot() as the source of truth.",
                "Expose metrics through session-state-like runtime state, not world snapshot.",
                "Keep client presentation-only and add contract test coverage.",
            ),
        ),
        CompareTask(
            task_id="java_idempotency_payment_callback",
            family="java",
            description="Payment callback handler applies duplicate provider events more than once.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the highest-risk business correctness bug and give the smallest safe fix. "
                "Prefer an idempotency fix over a broad architecture rewrite."
            ),
            max_tokens=1050,
            repeat_group="java-extended",
            context_files=(
                _java_file(
                    "src/main/java/com/example/payment/PaymentCallbackService.java",
                    """
                    package com.example.payment;

                    import java.time.Instant;

                    public class PaymentCallbackService {
                        private final PaymentRepository paymentRepository;
                        private final OutboxRepository outboxRepository;

                        public PaymentCallbackService(
                                PaymentRepository paymentRepository,
                                OutboxRepository outboxRepository) {
                            this.paymentRepository = paymentRepository;
                            this.outboxRepository = outboxRepository;
                        }

                        public void onCallback(PaymentCallback payload) {
                            Payment payment = paymentRepository.requireByOrderId(payload.getOrderId());
                            payment.markPaid(payload.getProviderTxnId(), Instant.parse(payload.getPaidAt()));
                            paymentRepository.save(payment);
                            outboxRepository.insert("PAYMENT_PAID", payload.getOrderId(), payload.getProviderTxnId());
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/PaymentCallback.java",
                    """
                    package com.example.payment;

                    public class PaymentCallback {
                        private String orderId;
                        private String providerTxnId;
                        private String paidAt;

                        public String getOrderId() {
                            return orderId;
                        }

                        public String getProviderTxnId() {
                            return providerTxnId;
                        }

                        public String getPaidAt() {
                            return paidAt;
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/Payment.java",
                    """
                    package com.example.payment;

                    import java.time.Instant;

                    public class Payment {
                        private String orderId;
                        private String providerTxnId;
                        private String status;
                        private Instant paidAt;

                        public void markPaid(String providerTxnId, Instant paidAt) {
                            this.providerTxnId = providerTxnId;
                            this.paidAt = paidAt;
                            this.status = "PAID";
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/PaymentRepository.java",
                    """
                    package com.example.payment;

                    public interface PaymentRepository {
                        Payment requireByOrderId(String orderId);
                        void save(Payment payment);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/payment/OutboxRepository.java",
                    """
                    package com.example.payment;

                    public interface OutboxRepository {
                        void insert(String topic, String orderId, String providerTxnId);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify duplicate callback / duplicate providerTxnId replays as the core bug.",
                "Prefer idempotency guard on providerTxnId or payment state before save/outbox.",
                "Keep the fix localized to callback flow or repository contract.",
                "Mention regression for replayed callbacks and outbox duplication.",
            ),
        ),
        CompareTask(
            task_id="java_outbox_publish_before_commit",
            family="java",
            description="Domain event is published inline before the database write is durably committed.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Identify the highest-risk consistency bug and propose the smallest safe fix. "
                "Do not redesign the whole eventing stack unless absolutely necessary."
            ),
            max_tokens=1050,
            repeat_group="java-extended",
            context_files=(
                _java_file(
                    "src/main/java/com/example/invoice/InvoiceService.java",
                    """
                    package com.example.invoice;

                    import java.time.Instant;

                    public class InvoiceService {
                        private final InvoiceRepository invoiceRepository;
                        private final DomainEventPublisher domainEventPublisher;

                        public InvoiceService(
                                InvoiceRepository invoiceRepository,
                                DomainEventPublisher domainEventPublisher) {
                            this.invoiceRepository = invoiceRepository;
                            this.domainEventPublisher = domainEventPublisher;
                        }

                        public void approve(long invoiceId, String approver) {
                            Invoice invoice = invoiceRepository.require(invoiceId);
                            invoice.approve(approver, Instant.now());
                            domainEventPublisher.publish("invoice.approved", invoiceId);
                            invoiceRepository.save(invoice);
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/invoice/DomainEventPublisher.java",
                    """
                    package com.example.invoice;

                    public interface DomainEventPublisher {
                        void publish(String eventType, long aggregateId);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/invoice/InvoiceRepository.java",
                    """
                    package com.example.invoice;

                    public interface InvoiceRepository {
                        Invoice require(long id);
                        void save(Invoice invoice);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify publish-before-commit inconsistency as the core bug.",
                "Prefer moving event creation to an outbox or after-commit boundary, not an async sleep/retry hack.",
                "Keep the proposed change minimal and localized.",
                "Mention regression where publish succeeds but save fails.",
            ),
        ),
        CompareTask(
            task_id="java_cache_stale_after_write",
            family="java",
            description="Profile update writes to DB but leaves the cache stale on the read path.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Review the write path and identify the highest-risk correctness bug. "
                "Propose the smallest safe fix with the right cache consistency behavior."
            ),
            max_tokens=950,
            repeat_group="java-extended",
            context_files=(
                _java_file(
                    "src/main/java/com/example/profile/ProfileService.java",
                    """
                    package com.example.profile;

                    public class ProfileService {
                        private final ProfileRepository profileRepository;
                        private final ProfileCache profileCache;

                        public ProfileService(ProfileRepository profileRepository, ProfileCache profileCache) {
                            this.profileRepository = profileRepository;
                            this.profileCache = profileCache;
                        }

                        public ProfileView get(long profileId) {
                            ProfileView cached = profileCache.get(profileId);
                            if (cached != null) {
                                return cached;
                            }
                            Profile profile = profileRepository.require(profileId);
                            ProfileView view = ProfileView.from(profile);
                            profileCache.put(profileId, view);
                            return view;
                        }

                        public void updateDisplayName(long profileId, String displayName) {
                            Profile profile = profileRepository.require(profileId);
                            profile.setDisplayName(displayName);
                            profileRepository.save(profile);
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/profile/ProfileCache.java",
                    """
                    package com.example.profile;

                    public interface ProfileCache {
                        ProfileView get(long profileId);
                        void put(long profileId, ProfileView view);
                        void evict(long profileId);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/profile/ProfileRepository.java",
                    """
                    package com.example.profile;

                    public interface ProfileRepository {
                        Profile require(long profileId);
                        void save(Profile profile);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify stale cache after write as the bug.",
                "Prefer evict or write-through in the update path, not a TTL-only workaround.",
                "Keep the change minimal in ProfileService/cache contract.",
                "Mention regression for immediate read-after-write.",
            ),
        ),
        CompareTask(
            task_id="java_csv_import_partial_batch",
            family="java",
            description="CSV batch import persists rows incrementally before the full batch is validated.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Find the highest-risk data consistency bug and propose the smallest safe fix. "
                "Avoid a full importer rewrite unless the snapshot forces it."
            ),
            max_tokens=1100,
            repeat_group="java-extended",
            context_files=(
                _java_file(
                    "src/main/java/com/example/importer/UserImportService.java",
                    """
                    package com.example.importer;

                    import java.util.List;

                    public class UserImportService {
                        private final CsvParser csvParser;
                        private final UserRepository userRepository;

                        public UserImportService(CsvParser csvParser, UserRepository userRepository) {
                            this.csvParser = csvParser;
                            this.userRepository = userRepository;
                        }

                        public void importCsv(String csvText) {
                            List<UserRow> rows = csvParser.parse(csvText);
                            for (UserRow row : rows) {
                                if (row.getEmail() == null || row.getEmail().isBlank()) {
                                    throw new IllegalArgumentException("email required");
                                }
                                userRepository.insert(row.getEmail(), row.getDisplayName());
                            }
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/importer/CsvParser.java",
                    """
                    package com.example.importer;

                    import java.util.List;

                    public interface CsvParser {
                        List<UserRow> parse(String csvText);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/importer/UserRepository.java",
                    """
                    package com.example.importer;

                    public interface UserRepository {
                        void insert(String email, String displayName);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify partial batch writes when a later row fails validation.",
                "Prefer upfront validation or transaction boundary over silent continue.",
                "Keep the fix localized to import flow.",
                "Mention regression for invalid row in the middle of the batch.",
            ),
        ),
        CompareTask(
            task_id="java_retry_duplicate_side_effect",
            family="java",
            description="Retry wrapper around a remote call duplicates the user-visible side effect.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Review the flow and identify the highest-risk bug. "
                "Propose the smallest safe fix and call out what must not be retried blindly."
            ),
            max_tokens=1050,
            repeat_group="java-extended",
            context_files=(
                _java_file(
                    "src/main/java/com/example/invoice/InvoiceNotificationService.java",
                    """
                    package com.example.invoice;

                    public class InvoiceNotificationService {
                        private final RetryExecutor retryExecutor;
                        private final InvoiceGateway invoiceGateway;
                        private final EmailGateway emailGateway;

                        public InvoiceNotificationService(
                                RetryExecutor retryExecutor,
                                InvoiceGateway invoiceGateway,
                                EmailGateway emailGateway) {
                            this.retryExecutor = retryExecutor;
                            this.invoiceGateway = invoiceGateway;
                            this.emailGateway = emailGateway;
                        }

                        public void send(long invoiceId) {
                            retryExecutor.run(() -> {
                                invoiceGateway.markSent(invoiceId);
                                emailGateway.sendInvoice(invoiceId);
                            });
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/invoice/RetryExecutor.java",
                    """
                    package com.example.invoice;

                    public interface RetryExecutor {
                        void run(Runnable action);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/invoice/InvoiceGateway.java",
                    """
                    package com.example.invoice;

                    public interface InvoiceGateway {
                        void markSent(long invoiceId);
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/invoice/EmailGateway.java",
                    """
                    package com.example.invoice;

                    public interface EmailGateway {
                        void sendInvoice(long invoiceId);
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify duplicate side effect under retry as the core bug.",
                "Call out that email sending must not be retried blindly with state mutation in the same block.",
                "Prefer moving the retry boundary or making one side idempotent.",
                "Mention regression for gateway timeout after markSent but before email send completes.",
            ),
        ),
        CompareTask(
            task_id="java_permission_scope_trust_bug",
            family="java",
            description="Service trusts orgId from request payload instead of the authenticated operator context.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Identify the highest-risk security bug and give the smallest maintainable fix. "
                "Prefer a clear trust-boundary correction over broad auth refactors."
            ),
            max_tokens=1000,
            repeat_group="java-extended",
            context_files=(
                _java_file(
                    "src/main/java/com/example/report/ReportController.java",
                    """
                    package com.example.report;

                    public class ReportController {
                        private final ReportService reportService;

                        public ReportController(ReportService reportService) {
                            this.reportService = reportService;
                        }

                        public ReportDto generate(UserSession session, GenerateReportRequest request) {
                            return reportService.generate(request.getOrgId(), session.getUserId(), request.getRange());
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/report/GenerateReportRequest.java",
                    """
                    package com.example.report;

                    public class GenerateReportRequest {
                        private long orgId;
                        private String range;

                        public long getOrgId() {
                            return orgId;
                        }

                        public String getRange() {
                            return range;
                        }
                    }
                    """,
                ),
                _java_file(
                    "src/main/java/com/example/report/UserSession.java",
                    """
                    package com.example.report;

                    public class UserSession {
                        private long userId;
                        private long orgId;

                        public long getUserId() {
                            return userId;
                        }

                        public long getOrgId() {
                            return orgId;
                        }
                    }
                    """,
                ),
            ),
            hidden_checklist=(
                "Identify trust-boundary bug: request orgId is untrusted compared with session orgId.",
                "Recommend session/context org as source of truth or explicit mismatch validation.",
                "Keep fix at controller/service boundary instead of auth subsystem rewrite.",
                "Mention regression for cross-org forged request payloads.",
            ),
        ),
        CompareTask(
            task_id="script_python_csv_reconcile",
            family="script",
            description="Write a Python reconciliation script for two daily business CSV exports with duplicate and blank-row edge cases.",
            developer_message=SCRIPT_DEVELOPER_MESSAGE,
            user_request=(
                "Write the smallest production-safe Python script or script skeleton to reconcile two CSV exports. "
                "State the exact matching strategy, the output files, and the key edge-case guards."
            ),
            max_tokens=1300,
            repeat_group="script-core",
            context_files=(
                _java_file(
                    "samples/finance_export.csv",
                    """
                    merchant_order_id,provider_txn_id,amount_cents,status,updated_at
                    O-1001,P-9001,12800,SETTLED,2026-03-08T10:00:01Z
                    O-1002,P-9002,12800,REFUNDED,2026-03-08T10:05:01Z
                    O-1003,P-9003,6500,SETTLED,2026-03-08T10:06:01Z
                    O-1003,P-9003,6500,SETTLED,2026-03-08T10:06:01Z
                    """,
                ),
                _java_file(
                    "samples/merchant_statement.csv",
                    """
                    merchant_order_id,provider_txn_id,amount_cents,status,updated_at
                    O-1001,P-9001,12800,SETTLED,2026-03-08T10:00:02Z
                    O-1002,P-9002,12800,REFUNDED,2026-03-08T10:04:59Z
                    O-1004,P-9004,9900,SETTLED,2026-03-08T10:07:01Z
                    """,
                ),
                _java_file(
                    "docs/reconcile_rules.md",
                    """
                    - Match by merchant_order_id first, then provider_txn_id as fallback.
                    - Flag duplicates, missing rows, stale refunds, and amount mismatches.
                    - Emit one machine-readable CSV and one human-readable summary.
                    - Tolerate BOM headers, duplicate header rows, and blank lines.
                    """,
                ),
            ),
            hidden_checklist=(
                "Use streaming/row-wise parsing instead of assuming tiny files.",
                "State primary and fallback match keys correctly.",
                "Handle BOM, blank lines, duplicate headers, and duplicate rows.",
                "Emit both machine-readable discrepancy output and human summary.",
            ),
        ),
        CompareTask(
            task_id="script_bash_log_triage",
            family="script",
            description="Write a shell script to summarize recurring production errors from mixed application logs.",
            developer_message=SCRIPT_DEVELOPER_MESSAGE,
            user_request=(
                "Write a production-safe Bash script or shell pipeline to summarize the top recurring error signatures. "
                "Ignore health checks and keep the script reviewable."
            ),
            max_tokens=1150,
            repeat_group="script-core",
            context_files=(
                _java_file(
                    "logs/app.log",
                    """
                    2026-03-08T10:00:01Z INFO healthcheck ok
                    2026-03-08T10:00:02Z ERROR OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409
                    2026-03-08T10:00:03Z ERROR OrderService failed to reserve inventory orderId=992 sku=abc code=INV-409
                    2026-03-08T10:00:05Z WARN healthcheck latency 82ms
                    2026-03-08T10:00:06Z ERROR PaymentGateway timeout providerTxnId=P-9001
                    2026-03-08T10:00:07Z ERROR PaymentGateway timeout providerTxnId=P-9002
                    2026-03-08T10:00:09Z ERROR ProfileService duplicate email email=alice@example.com
                    """,
                ),
                _java_file(
                    "docs/ops_requirement.md",
                    """
                    - Group similar errors into one signature by stripping ids, emails, timestamps, and txn values.
                    - Print top signatures sorted by count descending.
                    - Accept both plain text *.log and gzipped *.log.gz files.
                    - Ignore INFO/WARN healthcheck noise.
                    """,
                ),
            ),
            hidden_checklist=(
                "Use grep/awk/sed/sort or equivalent safely and explicitly.",
                "Normalize volatile ids before counting signatures.",
                "Ignore health check noise.",
                "Mention or implement .gz handling and deterministic descending sort.",
            ),
        ),
        CompareTask(
            task_id="script_python_jsonl_replay_analyzer",
            family="script",
            description="Write a small Python analyzer for replay JSONL files with malformed-line tolerance.",
            developer_message=SCRIPT_DEVELOPER_MESSAGE,
            user_request=(
                "Write the smallest production-safe Python script or skeleton to analyze replay JSONL files. "
                "Compute per-session turn counts, invalid-output counts, and malformed-line stats."
            ),
            max_tokens=1300,
            repeat_group="script-core",
            context_files=(
                _java_file(
                    "samples/replay.jsonl",
                    """
                    {"sessionId":"s1","type":"agent.turn","tick":10}
                    {"sessionId":"s1","type":"agent.turn","tick":11}
                    {"sessionId":"s1","type":"error","code":"invalid_output"}
                    {"sessionId":"s2","type":"agent.turn","tick":3}
                    not-json
                    {"sessionId":"s2","type":"error","code":"runtime_fault"}
                    """,
                ),
                _repo_file("apps/game-runtime/src/runtime/replay.ts"),
                _java_file(
                    "docs/analyzer_requirements.md",
                    """
                    - Input may be multi-GB; do not assume it fits in memory.
                    - Skip malformed lines but count them.
                    - Output one summary per session and one global footer.
                    - Keep the script dependency-free if possible.
                    """,
                ),
            ),
            hidden_checklist=(
                "Prefer streaming file iteration, not full-file load.",
                "Count malformed lines explicitly.",
                "Aggregate per-session turn and invalid-output counts.",
                "Keep the script simple and dependency-light.",
            ),
        ),
        CompareTask(
            task_id="script_bash_atomic_deploy",
            family="script",
            description="Write a deploy script that performs atomic release swap with health check and rollback.",
            developer_message=SCRIPT_DEVELOPER_MESSAGE,
            user_request=(
                "Write a small Bash deployment script or script skeleton for an atomic release rollout. "
                "It must be safe to review and safe to abort."
            ),
            max_tokens=1250,
            repeat_group="script-core",
            context_files=(
                _java_file(
                    "docs/deploy_requirements.md",
                    """
                    - New release is unpacked under /srv/myapp/releases/<timestamp>.
                    - Current live symlink is /srv/myapp/current.
                    - Health check endpoint is http://127.0.0.1:8080/healthz.
                    - On failure, restore previous symlink target.
                    - Keep logs under /srv/myapp/deploy.log.
                    """,
                ),
                _java_file(
                    "docs/ops_constraints.md",
                    """
                    - Use set -euo pipefail.
                    - Refuse to run if current symlink is missing.
                    - Do not delete previous release before health check succeeds.
                    - Print clear rollback messages.
                    """,
                ),
            ),
            hidden_checklist=(
                "Use set -euo pipefail and explicit variables.",
                "Preserve previous symlink target for rollback.",
                "Perform health check before deleting or finalizing.",
                "Keep the rollout atomic with symlink swap or equivalent.",
            ),
        ),
        CompareTask(
            task_id="ts_reconnect_circuit_breaker",
            family="ts",
            description="Reconnect handling risks bypassing the circuit breaker that protects the runtime loop.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Using the real project files below, identify the highest-risk reconnect safety bug and propose "
                "the smallest maintainable fix. Preserve the hard reconnect guard."
            ),
            max_tokens=1250,
            repeat_group="ts-extended",
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("apps/game-runtime/src/runtime/config.ts"),
                _repo_file("packages/protocol/src/messages.ts"),
                _repo_file("apps/game-client/src/App.tsx"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
            ),
            hidden_checklist=(
                "Respect maxReconnectAttempts as a hard safety guard.",
                "Keep reconnect authority in runtime, not client.",
                "Call out the exact reconnect state machine bug rather than generic retry advice.",
                "Mention integration or fault-injection coverage.",
            ),
        ),
        CompareTask(
            task_id="ts_build_atomic_write_guard",
            family="ts",
            description="Builder flow must preserve atomic writes and schema-first validation under partial failure.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Using the real project files below, identify the highest-risk build-flow consistency bug and "
                "propose the smallest safe fix. Preserve atomic content writes."
            ),
            max_tokens=1250,
            repeat_group="ts-extended",
            context_files=(
                _repo_file("apps/game-runtime/src/runtime/contentStore.ts"),
                _repo_file("apps/game-runtime/src/runtime/GameRuntimeServer.ts"),
                _repo_file("packages/protocol/src/build.ts"),
                _repo_file("apps/game-runtime/test/contentStore.test.ts"),
                _repo_file("apps/game-runtime/test/ui-contract.integration.test.ts"),
            ),
            hidden_checklist=(
                "Preserve tmp + rename atomic write behavior.",
                "Validate build operations against protocol schema before mutating content.",
                "Keep builder flow content-only and avoid runtime/client side mutations.",
                "Mention contentStore and integration test coverage.",
            ),
        ),
        CompareTask(
            task_id="extreme_restore_bootstrap_longctx",
            family="extreme",
            description="262K extreme restore/bootstrap reasoning with real runtime files plus repeated incident logs.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Given the oversized restore incident snapshot below, identify the highest-risk correctness bug, "
                "propose the smallest safe fix, and explain which exact files should change. Do not rewrite the subsystem."
            ),
            max_tokens=1800,
            repeat_group="extreme-core",
            context_files=(
                _generated_file("generated/extreme_restore_context.txt", _extreme_restore_context),
            ),
            hidden_checklist=(
                "Identify phase/thread bootstrap ordering as the real bug.",
                "Keep fix maintainable under large-context noise.",
                "Avoid proposing a broad subsystem rewrite.",
                "Mention test coverage for boot-time restore and thread recreation.",
            ),
        ),
        CompareTask(
            task_id="extreme_runtime_metrics_longctx",
            family="extreme",
            description="262K extreme protocol/runtime metrics task with repeated snapshots and real files.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Given the oversized runtime metrics snapshot below, propose the smallest protocol-first change set "
                "to expose metrics cleanly. Keep runtime authoritative and avoid UI-driven state."
            ),
            max_tokens=1800,
            repeat_group="extreme-core",
            context_files=(
                _generated_file("generated/extreme_metrics_context.txt", _extreme_metrics_context),
            ),
            hidden_checklist=(
                "Stay protocol-first despite the large context volume.",
                "Use runtime metrics snapshot as the source of truth.",
                "Prefer session-state-like exposure over world snapshot.",
                "Keep the answer concrete and bounded under long context.",
            ),
        ),
        CompareTask(
            task_id="extreme_java_change_impact_longctx",
            family="extreme",
            description="262K extreme Java incident with repeated service implementations and duplicate side-effect logs.",
            developer_message=COMMON_DEVELOPER_MESSAGE,
            user_request=(
                "Given the oversized Java approval incident below, identify the smallest safe change set that "
                "prevents duplicate user-visible side effects without redesigning the whole service layer."
            ),
            max_tokens=1700,
            repeat_group="extreme-core",
            context_files=(
                _generated_file("generated/extreme_java_change_impact.txt", _extreme_java_context),
            ),
            hidden_checklist=(
                "Identify duplicate side effect under retry or repeated execution.",
                "Keep the fix minimal under noisy repeated context.",
                "Avoid overfitting to one log line only.",
                "Mention regression for repeated notifications.",
            ),
        ),
        CompareTask(
            task_id="extreme_reconcile_script_longctx",
            family="extreme",
            description="262K extreme script-writing task with repeated reconciliation rules and sample exports.",
            developer_message=SCRIPT_DEVELOPER_MESSAGE,
            user_request=(
                "Given the oversized reconciliation specification below, write the smallest production-safe Python script "
                "or script skeleton to reconcile the feeds. Keep it stream-friendly and operationally realistic."
            ),
            max_tokens=1900,
            repeat_group="extreme-core",
            context_files=(
                _generated_file("generated/extreme_reconcile_script.txt", _extreme_script_context),
            ),
            hidden_checklist=(
                "Prefer streaming processing even under huge context.",
                "Use the documented primary/fallback match keys.",
                "Emit both machine-readable and human-readable outputs.",
                "Handle duplicate rows and malformed headers.",
            ),
        ),
    ]
