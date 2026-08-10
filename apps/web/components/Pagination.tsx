export default function Pagination({
  page,
  pageCount,
  onPageChange
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  if (pageCount <= 1) return null;
  return (
    <div className="pagination">
      <button className="pageButton" disabled={page <= 1} onClick={() => onPageChange(page - 1)} type="button">
        Prev
      </button>
      <span className="pageInfo">
        Page {page} of {pageCount}
      </span>
      <button className="pageButton" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)} type="button">
        Next
      </button>
    </div>
  );
}
