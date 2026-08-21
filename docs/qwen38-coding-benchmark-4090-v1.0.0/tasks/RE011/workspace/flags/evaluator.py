def is_enabled(user_id,config,overrides=None):return hash(user_id)%10000<config.basis_points
