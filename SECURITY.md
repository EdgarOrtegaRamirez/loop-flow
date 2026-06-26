# Security

## Security Considerations

### Data Storage
- LoopFlow stores iteration data in a local SQLite database (`~/.loopflow/loopflow.db`)
- No data is transmitted to external servers
- Database path can be customized via `--db` CLI flag

### Input Validation
- All CLI inputs are validated through Pydantic models
- File paths are not resolved or followed (stored as strings only)
- Error messages are stored as-is but truncated in display output

### No Network Access
- LoopFlow does not make any network requests
- No API keys or credentials are required
- No external dependencies with known vulnerabilities

### Recommendations
- Store the database file in an encrypted volume if iteration data is sensitive
- Regularly back up `~/.loopflow/loopflow.db`
- Use `clear` or `delete_session` to remove iterations containing sensitive information
