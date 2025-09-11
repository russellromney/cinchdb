"""MkDocs macros hooks."""
import os
import toml


def on_env(env, config, files):
    """Hook to define variables for MkDocs."""
    
    # Get version from environment or pyproject.toml
    version = os.environ.get('CINCHDB_VERSION')
    
    if not version:
        try:
            with open('pyproject.toml', 'r') as f:
                data = toml.load(f)
                version = data['project']['version']
        except:
            version = 'dev'
    
    env.variables['cinchdb_version'] = version
    return env