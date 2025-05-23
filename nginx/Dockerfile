FROM nginx:alpine

# Remove the default nginx.conf
RUN rm /etc/nginx/conf.d/default.conf

# Copy the custom configuration file
COPY nginx.config /etc/nginx/conf.d/default.conf

# Expose ports
EXPOSE 80 443

# Run nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
