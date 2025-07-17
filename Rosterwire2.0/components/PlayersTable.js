import React, { useEffect, useState, useMemo } from 'react';
import { useTable, useSortBy } from 'react-table';
import styles from '../styles/PlayersTable.module.css';

export default function PlayersTable() {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

useEffect(() => {
  fetch('http://localhost:5000/api/players') // Use full URL
    .then(res => res.json())
    .then(data => {
      setPlayers(data.players || []);
      setLoading(false);
    })
    .catch(err => {
      console.error('Failed to fetch players:', err);
      setLoading(false);
    });
}, []);

  const columns = useMemo(() => [
    { Header: 'Name', accessor: 'name' },
    { Header: 'Team', accessor: row => row.team.abbreviation, id: 'team' },
    { Header: 'Star Value', accessor: 'star_value' },
    { Header: 'PTS', accessor: row => row.last_season_stats.PTS || 0, id: 'pts' },
    { Header: 'REB', accessor: row => row.last_season_stats.REB || 0, id: 'reb' },
    { Header: 'AST', accessor: row => row.last_season_stats.AST || 0, id: 'ast' },
  ], []);

  const {
    getTableProps, getTableBodyProps,
    headerGroups, rows, prepareRow
  } = useTable({ columns, data: players }, useSortBy);

  if (loading) return <div className={styles.loading}>Loading NBA players...</div>;

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Rosterwire</h1>
      <table {...getTableProps()} className={styles.table}>
        <thead>
          {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map(column => (
                <th
                  {...column.getHeaderProps(column.getSortByToggleProps())}
                  className={styles.header}
                >
                  {column.render('Header')}
                  <span>
                    {column.isSorted
                      ? column.isSortedDesc ? ' 🔽' : ' 🔼'
                      : ''}
                  </span>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody {...getTableBodyProps()}>
          {rows.map(row => {
            prepareRow(row);
            return (
              <tr {...row.getRowProps()} className={styles.row}>
                {row.cells.map(cell => (
                  <td {...cell.getCellProps()} className={styles.cell}>
                    {cell.render('Cell')}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
