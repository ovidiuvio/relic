FROM pgsty/mc:RELEASE.2026-09-16T00-00-00Z

# Copy sync script
COPY sync.sh /usr/local/bin/sync.sh
RUN chmod +x /usr/local/bin/sync.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/sync.sh"]
