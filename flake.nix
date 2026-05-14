{
  description = "Textual TUI for declarative MIME app management in a NixOS/Home Manager repo";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pythonEnv = pkgs.python3.withPackages (ps: [
            ps.textual
          ]);
        in
        {
          default = pkgs.writeShellApplication {
            name = "nixos-mimeapps-ui";
            runtimeInputs = [ pythonEnv ];
            text = ''
              export PYTHONPATH="${./src}:''${PYTHONPATH:-}"
              exec python -m nixosmimeappsui.cli "$@"
            '';
          };
        });

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/nixos-mimeapps-ui";
        };
      });

      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              python3Packages.textual
              python3Packages.pytest
            ];
          };
        });
    };
}
