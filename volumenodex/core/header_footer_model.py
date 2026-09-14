"""Header and footer data model supporting per-page customization and token expansion."""

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any
from datetime import datetime


@dataclass
class PageHeaderFooterConfig:
    """Header and footer text and options for a specific page or default template."""
    header_left: str = ""
    header_center: str = ""
    header_right: str = ""
    footer_left: str = ""
    footer_center: str = "— {page} —"
    footer_right: str = ""
    suppressed: bool = False
    is_custom: bool = False  # If True, page is unlinked from document default
    is_linked_to_previous: bool = True

    @property
    def left_header(self) -> str: return self.header_left
    @left_header.setter
    def left_header(self, v: str): self.header_left = v

    @property
    def center_header(self) -> str: return self.header_center
    @center_header.setter
    def center_header(self, v: str): self.header_center = v

    @property
    def right_header(self) -> str: return self.header_right
    @right_header.setter
    def right_header(self, v: str): self.header_right = v

    @property
    def left_footer(self) -> str: return self.footer_left
    @left_footer.setter
    def left_footer(self, v: str): self.footer_left = v

    @property
    def center_footer(self) -> str: return self.footer_center
    @center_footer.setter
    def center_footer(self, v: str): self.footer_center = v

    @property
    def right_footer(self) -> str: return self.footer_right
    @right_footer.setter
    def right_footer(self, v: str): self.footer_right = v


@dataclass
class HeaderFooterModel:
    """Manages document running headers, footers, and per-page differentiation."""
    different_first_page: bool = True
    first_page_config: PageHeaderFooterConfig = field(
        default_factory=lambda: PageHeaderFooterConfig(suppressed=True, is_custom=True)
    )
    default_config: PageHeaderFooterConfig = field(default_factory=PageHeaderFooterConfig)
    page_overrides: Dict[int, PageHeaderFooterConfig] = field(default_factory=dict)

    def get_config_for_page(self, page_num: int) -> PageHeaderFooterConfig:
        """Returns the effective header/footer config for a 1-indexed page."""
        if page_num == 1 and self.different_first_page:
            return self.first_page_config
        if page_num in self.page_overrides:
            return self.page_overrides[page_num]
        return self.default_config

    def set_page_override(self, page_num: int, config: PageHeaderFooterConfig) -> None:
        """Sets or unlinks a custom header/footer configuration for a specific page."""
        config.is_custom = True
        self.page_overrides[page_num] = config

    def unlink_page(self, page_num: int) -> PageHeaderFooterConfig:
        """Creates a custom decoupled copy of the default config for a page."""
        if page_num == 1 and self.different_first_page:
            return self.first_page_config
        cfg = PageHeaderFooterConfig(
            header_left=self.default_config.header_left,
            header_center=self.default_config.header_center,
            header_right=self.default_config.header_right,
            footer_left=self.default_config.footer_left,
            footer_center=self.default_config.footer_center,
            footer_right=self.default_config.footer_right,
            suppressed=False,
            is_custom=True,
        )
        self.page_overrides[page_num] = cfg
        return cfg

    def link_page_to_default(self, page_num: int) -> None:
        """Removes page override so it inherits the default header/footer."""
        if page_num == 1:
            self.different_first_page = False
        else:
            self.page_overrides.pop(page_num, None)

    @staticmethod
    def expand_tokens(
        template: str,
        page_num: Any = 1,
        total_pages: int = 1,
        title: str = "",
        author: str = "",
        date: str = "",
    ) -> str:
        """Expands variables like {page}, {total}, {title}, {author}, {date}."""
        if not template:
            return ""
        if isinstance(page_num, dict):
            tokens = page_num
            p = tokens.get("page", 1)
            t = tokens.get("total", 1)
            ti = tokens.get("title", "")
            au = tokens.get("author", "")
            dt = tokens.get("date", "")
            return HeaderFooterModel.expand_tokens(template, p, t, ti, au, dt)

        now_str = date or datetime.now().strftime("%B %d, %Y")
        res = template.replace("{page}", str(page_num))
        res = res.replace("{total}", str(max(1, total_pages)))
        res = res.replace("{title}", title or "Untitled Document")
        res = res.replace("{author}", author or "")
        res = res.replace("{date}", now_str)
        return res

    def to_dict(self) -> Dict[str, Any]:
        return {
            "different_first_page": self.different_first_page,
            "first_page_config": asdict(self.first_page_config),
            "default_config": asdict(self.default_config),
            "page_overrides": {str(k): asdict(v) for k, v in self.page_overrides.items()},
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "HeaderFooterModel":
        if not data:
            return cls()
        diff_first = data.get("different_first_page", True)
        f_cfg_data = data.get("first_page_config", {})
        d_cfg_data = data.get("default_config", {})
        first_cfg = PageHeaderFooterConfig(**f_cfg_data) if f_cfg_data else PageHeaderFooterConfig(suppressed=True, is_custom=True)
        default_cfg = PageHeaderFooterConfig(**d_cfg_data) if d_cfg_data else PageHeaderFooterConfig()

        overrides = {}
        for k, v in data.get("page_overrides", {}).items():
            try:
                overrides[int(k)] = PageHeaderFooterConfig(**v)
            except Exception:
                pass

        return cls(
            different_first_page=diff_first,
            first_page_config=first_cfg,
            default_config=default_cfg,
            page_overrides=overrides,
        )
