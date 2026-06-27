import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
  onLimitChange?: (limit: number) => void;
  pageSizes?: number[];
  isLoading?: boolean;
}

const DEFAULT_PAGE_SIZES = [25, 50, 100, 200];

export function Pagination({
  total,
  limit,
  offset,
  onOffsetChange,
  onLimitChange,
  pageSizes = DEFAULT_PAGE_SIZES,
  isLoading = false,
}: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
  const canBack = offset > 0;
  const canForward = offset + limit < total;

  return (
    <div className="flex items-center justify-between px-md py-sm border-t border-outline-variant text-body-sm text-on-surface-variant">
      <span>
        {total === 0
          ? "No records"
          : `Showing ${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
      </span>

      <div className="flex items-center gap-sm">
        {onLimitChange && (
          <select
            value={limit}
            onChange={(e) => {
              onLimitChange(Number(e.target.value));
              onOffsetChange(0);
            }}
            className="form-select w-auto pr-6 text-xs"
            aria-label="Rows per page"
            disabled={isLoading}
          >
            {pageSizes.map((s) => (
              <option key={s} value={s}>
                {s} rows
              </option>
            ))}
          </select>
        )}

        <span className="text-label-md">
          Page {currentPage} of {pageCount}
        </span>

        <button
          className="btn-icon p-xs"
          disabled={!canBack || isLoading}
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
          aria-label="Previous page"
        >
          <ChevronLeft size={16} />
        </button>

        <button
          className="btn-icon p-xs"
          disabled={!canForward || isLoading}
          onClick={() => onOffsetChange(offset + limit)}
          aria-label="Next page"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
