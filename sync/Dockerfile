FROM minio/mc:latest

# Copy sync script
COPY sync.sh /usr/local/bin/sync.sh
RUN chmod +x /usr/local/bin/sync.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/sync.sh"]
