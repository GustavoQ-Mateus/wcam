export type Surface = "console" | "phone";

export interface Health {
  status: "ok";
  version: string;
  surface: Surface;
}

export interface ErrorBody {
  error: {
    code: string;
    message: string;
  };
}
