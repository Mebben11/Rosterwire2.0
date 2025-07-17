'use client';

import { useEffect, useState, useMemo } from 'react';
import { useTable, useSortBy } from 'react-table';
import styles from '../styles/PlayersTable.module.css';

export default function Home() {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetch('http://localhost:5000/api/players')
      .then((res) => res.json())
      .then((data) => {
        setPlayers(data.players || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch players:', err);
        setLoading(false);
      });
  }, []);

  // Filter players by name or team abbreviation based on search term
  const filteredPlayers = useMemo(() => {
    if (!searchTerm) return players;

    const lowerSearch = searchTerm.toLowerCase();
    return players.filter(
      (player) =>
        player.name.toLowerCase().includes(lowerSearch) ||
        (player.team.abbreviation || '').toLowerCase().includes(lowerSearch)
    );
  }, [players, searchTerm]);

  const columns = useMemo(
    () => [
      { Header: 'Name', accessor: 'name' },
      {
        Header: 'Team',
        accessor: (row) => row.team.abbreviation || 'N/A',
        id: 'team',
      },
      {
        Header: '⭐',
        accessor: 'star_value',
        Cell: ({ value }) =>
          '★'.repeat(Math.round(value)) + '☆'.repeat(5 - Math.round(value)),
      },
      {
        Header: 'PTS',
        accessor: (row) =>
          row.last_season_stats.PTS?.toFixed(1) || '0.0',
        id: 'pts',
      },
      {
        Header: 'REB',
        accessor: (row) =>
          row.last_season_stats.REB?.toFixed(1) || '0.0',
        id: 'reb',
      },
      {
        Header: 'AST',
        accessor: (row) =>
          row.last_season_stats.AST?.toFixed(1) || '0.0',
        id: 'ast',
      },
    ],
    []
  );

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
  } = useTable({ columns, data: filteredPlayers }, useSortBy);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Rosterwire</h1>

      <input
        type="text"
        placeholder="Search by player or team..."
        className={styles.searchInput}
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />

      {loading ? (
        <div className={styles.loading}>Loading NBA players...</div>
      ) : (
        <table {...getTableProps()} className={styles.table}>
          <thead>
            {headerGroups.map((headerGroup) => (
              <tr {...headerGroup.getHeaderGroupProps()} key={headerGroup.id}>
                {headerGroup.headers.map((column) => (
                  <th
                    {...column.getHeaderProps(column.getSortByToggleProps())}
                    key={column.id}
                  >
                    {column.render('Header')}
                    <span className={styles.headerArrow}>
                      {column.isSorted
                        ? column.isSortedDesc
                          ? ' 🔽'
                          : ' 🔼'
                        : ''}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody {...getTableBodyProps()}>
            {rows.map((row) => {
              prepareRow(row);
              return (
                <tr {...row.getRowProps()} key={row.id}>
                  {row.cells.map((cell) => (
                    <td {...cell.getCellProps()} key={cell.column.id}>
                      {cell.render('Cell')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
